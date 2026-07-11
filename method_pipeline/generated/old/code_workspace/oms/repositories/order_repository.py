"""
Order repository for order-specific database operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oms.models.entities import Order, OrderStatus, OrderLineItem
from oms.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """
    Repository for Order entity operations.
    
    Extends BaseRepository with order-specific queries including status filtering,
    customer orders, and order analytics.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize order repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(Order, session)
    
    async def get_with_line_items(self, order_id: int) -> Optional[Order]:
        """
        Get order with line items eagerly loaded.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order instance with line items or None if not found
        """
        query = select(Order).options(
            selectinload(Order.line_items).selectinload(OrderLineItem.product)
        ).where(Order.id == order_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_orders_by_customer(
        self, customer_id: int, limit: int = 50, offset: int = 0
    ) -> List[Order]:
        """
        Get orders for a specific customer.
        
        Args:
            customer_id: Customer ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of order instances for the customer
        """
        query = select(Order).where(
            Order.customer_id == customer_id
        ).order_by(
            Order.created_at.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_orders_by_status(
        self, status: OrderStatus, limit: int = 100, offset: int = 0
    ) -> List[Order]:
        """
        Get orders by status.
        
        Args:
            status: Order status to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of order instances with the specified status
        """
        query = select(Order).where(
            Order.status == status
        ).order_by(
            Order.created_at.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_orders(self, limit: int = 100) -> List[Order]:
        """
        Get all pending orders awaiting review.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of pending order instances
        """
        query = select(Order).where(
            Order.status == OrderStatus.PENDING
        ).order_by(
            Order.created_at.asc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_orders_for_shipping(self, limit: int = 100) -> List[Order]:
        """
        Get paid orders ready for shipping.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of paid order instances ready for shipping
        """
        query = select(Order).where(
            Order.status == OrderStatus.PAID
        ).order_by(
            Order.created_at.asc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count_by_status(self, status: OrderStatus) -> int:
        """
        Count orders by status.
        
        Args:
            status: Order status to count
            
        Returns:
            Count of orders with the specified status
        """
        query = select(func.count()).select_from(Order).where(Order.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_orders_in_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> List[Order]:
        """
        Get orders within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of results
            
        Returns:
            List of orders within the date range
        """
        query = select(Order).where(
            Order.created_at >= start_date
        ).where(
            Order.created_at <= end_date
        ).order_by(
            Order.created_at.desc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_total_revenue(self) -> float:
        """
        Calculate total revenue from completed orders.
        
        Returns:
            Total revenue amount
        """
        query = select(func.sum(Order.total_amount)).where(
            Order.status == OrderStatus.COMPLETED
        )
        result = await self.session.execute(query)
        return float(result.scalar() or 0)
