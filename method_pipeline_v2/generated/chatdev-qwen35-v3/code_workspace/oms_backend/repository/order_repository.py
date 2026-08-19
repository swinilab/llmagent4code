"""
Order repository with CRUD operations and state machine validation
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.domain.models import Order, OrderStatus
from oms_backend.domain.schemas import OrderCreate


class OrderRepository:
    """Repository for Order entity operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: OrderCreate, total_amount: float, line_items: list) -> Order:
        """Create a new order"""
        order = Order(
            customer_ref=data.customerRef,
            line_items=line_items,
            total_amount=total_amount,
            status=OrderStatus.PLACED,
            invoice_ref=None
        )
        self.session.add(order)
        await self.session.flush()
        return order
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Order]:
        """Get all orders with pagination"""
        result = await self.session.execute(
            select(Order).offset(offset).limit(limit)
        )
        return result.scalars().all()
    
    async def update_status(self, order_id: str, new_status: OrderStatus) -> Optional[Order]:
        """Update order status with state machine validation"""
        order = await self.get_by_id(order_id)
        if not order:
            return None
        
        # State machine validation
        valid_transitions = {
            OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
            OrderStatus.ACCEPTED: [OrderStatus.INVOICED, OrderStatus.CANCELLED],
            OrderStatus.INVOICED: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.VERIFIED],
            OrderStatus.VERIFIED: [OrderStatus.SHIPPED],
            OrderStatus.SHIPPED: [OrderStatus.CLOSED],
            OrderStatus.CLOSED: [],
            OrderStatus.CANCELLED: [],
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            raise ValueError(f"Invalid status transition from {order.status} to {new_status}")
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        await self.session.flush()
        return order
    
    async def set_invoice_ref(self, order_id: str, invoice_id: str) -> Optional[Order]:
        """Set invoice reference on order"""
        order = await self.get_by_id(order_id)
        if not order:
            return None
        
        order.invoice_ref = invoice_id
        order.status = OrderStatus.INVOICED
        order.updated_at = datetime.utcnow()
        await self.session.flush()
        return order
    
    async def update(self, order_id: str, data: dict) -> Optional[Order]:
        """Update order fields"""
        await self.session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(**data, updated_at=datetime.utcnow())
        )
        return await self.get_by_id(order_id)
    
    async def delete(self, order_id: str) -> bool:
        """Delete order"""
        order = await self.get_by_id(order_id)
        if order:
            await self.session.delete(order)
            return True
        return False
