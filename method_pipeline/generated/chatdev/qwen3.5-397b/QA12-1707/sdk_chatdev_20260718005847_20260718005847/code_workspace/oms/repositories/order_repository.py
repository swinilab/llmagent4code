"""
Order repository for data access operations.
Handles order and order line item operations.
"""

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from oms.models.order import Order, OrderStatus, OrderLineItem
from oms.models.order import OrderCreate, OrderLineItemCreate


class OrderRepository:
    """
    Repository for Order entity operations.
    Provides CRUD operations with async support and order lifecycle management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get an order by ID with line items."""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_customer_id(self, customer_id: int, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders for a customer."""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_status(self, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get orders by status."""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders with pagination."""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_pending_orders_count(self) -> int:
        """Get count of pending orders for queue management."""
        result = await self.session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
        )
        return result.scalar() or 0
    
    async def create(self, order_data: OrderCreate) -> Order:
        """Create a new order with line items."""
        order = Order(
            customer_id=order_data.customer_id,
            status=OrderStatus.PENDING,
            currency="USD",
            notes=order_data.notes,
            total_amount=0,
        )
        self.session.add(order)
        await self.session.flush()
        
        total_amount = 0
        for line_item_data in order_data.line_items:
            from oms.models.product import Product
            product_result = await self.session.execute(
                select(Product).where(Product.id == line_item_data.product_id)
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise ValueError(f"Product {line_item_data.product_id} not found")
            
            subtotal = line_item_data.quantity * float(product.base_price)
            line_item = OrderLineItem(
                order_id=order.id,
                product_id=line_item_data.product_id,
                quantity=line_item_data.quantity,
                unit_price=product.base_price,
                subtotal=subtotal,
            )
            self.session.add(line_item)
            total_amount += subtotal
        
        order.total_amount = total_amount
        await self.session.flush()
        await self.session.refresh(order)
        
        # Reload order with line_items for proper serialization
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.id == order.id)
        )
        return result.scalar_one()
    
    async def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Update order status."""
        order = await self.get_by_id(order_id)
        if not order:
            return None
        
        order.status = status
        await self.session.flush()
        await self.session.refresh(order)
        return order
    
    async def update(self, order_id: int, **kwargs) -> Optional[Order]:
        """Update an order."""
        order = await self.get_by_id(order_id)
        if not order:
            return None
        
        for field, value in kwargs.items():
            setattr(order, field, value)
        
        await self.session.flush()
        await self.session.refresh(order)
        return order
    
    async def delete(self, order_id: int) -> bool:
        """Delete an order by ID."""
        order = await self.get_by_id(order_id)
        if not order:
            return False
        
        await self.session.delete(order)
        await self.session.flush()
        return True
    
    async def count(self) -> int:
        """Get total number of orders."""
        result = await self.session.execute(select(func.count()).select_from(Order))
        return result.scalar() or 0
    
    async def set_invoice_ref(self, order_id: int, invoice_id: int) -> Optional[Order]:
        """Set invoice reference for an order."""
        order = await self.get_by_id(order_id)
        if not order:
            return None
        
        order.invoice_id = invoice_id
        await self.session.flush()
        await self.session.refresh(order)
        return order
