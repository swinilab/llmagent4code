"""
Order service for order-related business logic.

Handles the complete order lifecycle from creation to completion.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import (
    Order,
    OrderStatus,
    OrderLineItem,
    PaymentStatus,
    InvoiceStatus,
)
from oms.models.schemas import OrderCreate, OrderResponse, OrderUpdateStatus
from oms.repositories.order_repository import OrderRepository
from oms.repositories.product_repository import ProductRepository
from oms.repositories.payment_repository import PaymentRepository
from oms.repositories.invoice_repository import InvoiceRepository


class OrderService:
    """
    Service for managing order operations.
    
    Handles the complete order workflow:
    1. Customer places order (PENDING)
    2. Order Staff reviews & accepts (ACCEPTED)
    3. Accountant creates invoice (INVOICED)
    4. Customer pays invoice (PAID)
    5. Order Staff ships order (SHIPPED)
    6. Order Staff closes order (COMPLETED)
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize order service.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.repository = OrderRepository(session)
        self.product_repository = ProductRepository(session)
        self.payment_repository = PaymentRepository(session)
        self.invoice_repository = InvoiceRepository(session)
        self.session = session
    
    async def create_order(self, order_data: OrderCreate) -> OrderResponse:
        """
        Create a new order (Customer places order).
        
        Args:
            order_data: Order creation data including line items
            
        Returns:
            Created order response
            
        Raises:
            ValueError: If product not available or insufficient stock
        """
        total_amount = Decimal("0")
        line_items_data = []
        
        for item in order_data.line_items:
            product = await self.product_repository.get(item.product_id)
            if product is None:
                raise ValueError(f"Product {item.product_id} not found")
            if not product.is_available:
                raise ValueError(f"Product {item.product_id} is not available")
            if product.stock_quantity < item.quantity:
                raise ValueError(
                    f"Insufficient stock for product {item.product_id}. "
                    f"Available: {product.stock_quantity}, Requested: {item.quantity}"
                )
            
            subtotal = product.base_price * item.quantity
            total_amount += subtotal
            line_items_data.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": product.base_price,
                "subtotal": subtotal,
            })
        
        order = Order(
            customer_id=order_data.customer_id,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            currency=order_data.currency,
            shipping_address=order_data.shipping_address,
            notes=order_data.notes,
        )
        
        created_order = await self.repository.create(order)
        
        for item_data in line_items_data:
            line_item = OrderLineItem(
                order_id=created_order.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"],
            )
            self.session.add(line_item)
        
        for item_data in line_items_data:
            await self.product_repository.update_stock(
                item_data["product_id"], -item_data["quantity"]
            )
        
        await self.session.flush()
        
        order_with_items = await self.repository.get_with_line_items(created_order.id)
        return OrderResponse.model_validate(order_with_items)
    
    async def get_order(self, order_id: int) -> Optional[OrderResponse]:
        """
        Get order by ID with line items.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order response or None if not found
        """
        order = await self.repository.get_with_line_items(order_id)
        if order is None:
            return None
        return OrderResponse.model_validate(order)
    
    async def get_all_orders(
        self, limit: int = 100, offset: int = 0
    ) -> List[OrderResponse]:
        """
        Get all orders with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of order responses
        """
        orders = await self.repository.get_all(limit=limit, offset=offset)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_orders_by_customer(
        self, customer_id: int, limit: int = 50, offset: int = 0
    ) -> List[OrderResponse]:
        """
        Get orders for a specific customer.
        
        Args:
            customer_id: Customer ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of order responses
        """
        orders = await self.repository.get_orders_by_customer(
            customer_id, limit=limit, offset=offset
        )
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_orders_by_status(
        self, status: OrderStatus, limit: int = 100, offset: int = 0
    ) -> List[OrderResponse]:
        """
        Get orders by status.
        
        Args:
            status: Order status to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of order responses
        """
        orders = await self.repository.get_orders_by_status(
            status, limit=limit, offset=offset
        )
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_pending_orders(self, limit: int = 100) -> List[OrderResponse]:
        """
        Get all pending orders awaiting review.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of pending order responses
        """
        orders = await self.repository.get_pending_orders(limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def review_order(
        self, order_id: int, accept: bool, notes: Optional[str] = None
    ) -> Optional[OrderResponse]:
        """
        Review and accept/reject an order (Order Staff action).
        
        Args:
            order_id: Order ID
            accept: True to accept, False to reject
            notes: Optional notes for the review
            
        Returns:
            Updated order response or None if not found
            
        Raises:
            ValueError: If order is not in PENDING status
        """
        order = await self.repository.get(order_id)
        if order is None:
            return None
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} is not in PENDING status")
        
        order.status = OrderStatus.ACCEPTED if accept else OrderStatus.REJECTED
        order.notes = notes if notes else order.notes
        
        if not accept:
            for line_item in order.line_items:
                await self.product_repository.update_stock(
                    line_item.product_id, line_item.quantity
                )
        
        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)
    
    async def update_order_status(
        self, order_id: int, status_update: OrderUpdateStatus
    ) -> Optional[OrderResponse]:
        """
        Update order status with validation.
        
        Args:
            order_id: Order ID
            status_update: Status update data
            
        Returns:
            Updated order response or None if not found
        """
        order = await self.repository.get(order_id)
        if order is None:
            return None
        
        order.status = status_update.status
        if status_update.notes:
            order.notes = status_update.notes
        
        if status_update.status == OrderStatus.SHIPPED:
            order.shipped_at = datetime.utcnow()
        elif status_update.status == OrderStatus.COMPLETED:
            order.completed_at = datetime.utcnow()
        
        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)
    
    async def ship_order(self, order_id: int) -> Optional[OrderResponse]:
        """
        Ship a paid order (Order Staff action).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order response or None if not found
            
        Raises:
            ValueError: If order is not in PAID status
        """
        order = await self.repository.get(order_id)
        if order is None:
            return None
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Order {order_id} is not in PAID status")
        
        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.utcnow()
        
        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)
    
    async def complete_order(self, order_id: int) -> Optional[OrderResponse]:
        """
        Complete a shipped order (Order Staff action).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order response or None if not found
            
        Raises:
            ValueError: If order is not in SHIPPED status
        """
        order = await self.repository.get(order_id)
        if order is None:
            return None
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Order {order_id} is not in SHIPPED status")
        
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        
        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)
    
    async def cancel_order(self, order_id: int) -> Optional[OrderResponse]:
        """
        Cancel an order and restore stock.
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order response or None if not found
            
        Raises:
            ValueError: If order cannot be cancelled
        """
        order = await self.repository.get(order_id)
        if order is None:
            return None
        if order.status in [OrderStatus.SHIPPED, OrderStatus.COMPLETED]:
            raise ValueError(f"Order {order_id} cannot be cancelled after shipping")
        
        order.status = OrderStatus.CANCELLED
        
        for line_item in order.line_items:
            await self.product_repository.update_stock(
                line_item.product_id, line_item.quantity
            )
        
        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)
    
    async def get_orders_for_shipping(self, limit: int = 100) -> List[OrderResponse]:
        """
        Get paid orders ready for shipping.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of order responses ready for shipping
        """
        orders = await self.repository.get_orders_for_shipping(limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_total_revenue(self) -> float:
        """
        Get total revenue from completed orders.
        
        Returns:
            Total revenue amount
        """
        return await self.repository.get_total_revenue()
