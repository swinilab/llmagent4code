"""
Order Service - Business logic for Order operations.
Handles the complete order lifecycle from creation to completion.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import (
    OrderModel,
    OrderItemModel,
    ProductModel,
    OrderStatusEnum,
    InvoiceModel,
)
from shared.models import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderItem,
    OrderStatus,
)


class OrderService:
    """Service class for Order business operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db_session

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """
        Get an order by its unique identifier.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel)
            .where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            return self._to_domain_model(order)
        return None

    async def get_orders_by_customer_id(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """
        Get all orders for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Order objects
        """
        result = await self.db.execute(
            select(OrderModel)
            .where(OrderModel.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        orders = result.scalars().all()
        return [self._to_domain_model(o) for o in orders]

    async def get_orders_by_status(
        self, status: OrderStatus, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """
        Get all orders with a specific status.
        
        Args:
            status: Order status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Order objects
        """
        result = await self.db.execute(
            select(OrderModel)
            .where(OrderModel.status == OrderStatusEnum(status.value))
            .offset(skip)
            .limit(limit)
        )
        orders = result.scalars().all()
        return [self._to_domain_model(o) for o in orders]

    async def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """
        Get all orders with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Order objects
        """
        result = await self.db.execute(
            select(OrderModel)
            .offset(skip)
            .limit(limit)
        )
        orders = result.scalars().all()
        return [self._to_domain_model(o) for o in orders]

    async def get_order_count(self) -> int:
        """
        Get the total number of orders.
        
        Returns:
            Total count of orders
        """
        result = await self.db.execute(
            select(func.count()).select_from(OrderModel)
        )
        return result.scalar() or 0

    async def create_order(self, order_data: OrderCreate) -> Order:
        """
        Create a new order placed by a customer.
        
        Args:
            order_data: OrderCreate object with order information
            
        Returns:
            Created Order object
        """
        # Calculate total amount from items
        total_amount = sum(item.subtotal for item in order_data.items)
        
        # Create order
        order = OrderModel(
            customer_id=order_data.customer_id,
            status=OrderStatusEnum.PENDING,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            notes=order_data.notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(order)
        await self.db.flush()  # Get the order ID
        
        # Create order items
        for item in order_data.items:
            order_item = OrderItemModel(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            self.db.add(order_item)
            
            # Update product stock
            await self._decrease_product_stock(item.product_id, item.quantity)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def accept_order(self, order_id: int) -> Optional[Order]:
        """
        Accept an order (Order Staff action).
        Changes status from PENDING to ACCEPTED.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        if order.status != OrderStatusEnum.PENDING:
            raise ValueError(f"Order {order_id} cannot be accepted. Current status: {order.status.value}")
        
        order.status = OrderStatusEnum.ACCEPTED
        order.accepted_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def update_order(
        self, order_id: int, order_data: OrderUpdate
    ) -> Optional[Order]:
        """
        Update an existing order.
        
        Args:
            order_id: The unique order ID
            order_data: OrderUpdate object with updated information
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        # Update fields if provided
        if order_data.status is not None:
            order.status = OrderStatusEnum(order_data.status.value)
        if order_data.shipping_address is not None:
            order.shipping_address = order_data.shipping_address
        if order_data.notes is not None:
            order.notes = order_data.notes
        
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def set_order_invoice(self, order_id: int, invoice_id: int) -> Optional[Order]:
        """
        Set the invoice ID for an order (when invoice is created).
        
        Args:
            order_id: The unique order ID
            invoice_id: The invoice ID to associate
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        order.invoice_id = invoice_id
        order.status = OrderStatusEnum.INVOICED
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def mark_order_paid(self, order_id: int) -> Optional[Order]:
        """
        Mark an order as paid (after payment is completed).
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        order.status = OrderStatusEnum.PAID
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def ship_order(self, order_id: int) -> Optional[Order]:
        """
        Ship an order (Order Staff action after payment).
        Changes status from PAID to SHIPPED.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        if order.status != OrderStatusEnum.PAID:
            raise ValueError(f"Order {order_id} cannot be shipped. Current status: {order.status.value}. Order must be paid before shipping.")
        
        order.status = OrderStatusEnum.SHIPPED
        order.shipped_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def complete_order(self, order_id: int) -> Optional[Order]:
        """
        Complete/close an order (Order Staff action after shipping).
        Changes status from SHIPPED to COMPLETED.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        if order.status != OrderStatusEnum.SHIPPED:
            raise ValueError(f"Order {order_id} cannot be completed. Current status: {order.status.value}")
        
        order.status = OrderStatusEnum.COMPLETED
        order.completed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def cancel_order(self, order_id: int) -> Optional[Order]:
        """
        Cancel an order.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        if order.status in [OrderStatusEnum.SHIPPED, OrderStatusEnum.COMPLETED]:
            raise ValueError(f"Order {order_id} cannot be cancelled. Current status: {order.status.value}")
        
        order.status = OrderStatusEnum.CANCELLED
        order.updated_at = datetime.utcnow()
        
        # Restore product stock
        for item in order.items:
            await self._increase_product_stock(item.product_id, item.quantity)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return self._to_domain_model(order)

    async def delete_order(self, order_id: int) -> bool:
        """
        Delete an order by its ID.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return False
        
        await self.db.delete(order)
        await self.db.commit()
        return True

    async def _decrease_product_stock(self, product_id: int, quantity: int):
        """Decrease product stock quantity."""
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product:
            product.stock_quantity = max(0, product.stock_quantity - quantity)
            product.updated_at = datetime.utcnow()

    async def _increase_product_stock(self, product_id: int, quantity: int):
        """Increase product stock quantity (for cancellations)."""
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product:
            product.stock_quantity += quantity
            product.updated_at = datetime.utcnow()

    def _to_domain_model(self, order_model: OrderModel) -> Order:
        """
        Convert SQLAlchemy model to domain model.
        
        Args:
            order_model: SQLAlchemy OrderModel object
            
        Returns:
            Domain Order object
        """
        items = [
            OrderItem(
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in order_model.items
        ]
        
        return Order(
            id=order_model.id,
            customer_id=order_model.customer_id,
            items=items,
            total_amount=order_model.total_amount,
            shipping_address=order_model.shipping_address,
            notes=order_model.notes,
            status=OrderStatus(order_model.status.value),
            invoice_id=order_model.invoice_id,
            created_at=order_model.created_at,
            updated_at=order_model.updated_at,
            accepted_at=order_model.accepted_at,
            shipped_at=order_model.shipped_at,
            completed_at=order_model.completed_at,
        )
