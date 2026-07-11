"""
Payment repository for payment-specific database operations.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Payment, PaymentStatus
from oms.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """
    Repository for Payment entity operations.
    
    Extends BaseRepository with payment-specific queries including status filtering
    and transaction lookups.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize payment repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(Payment, session)
    
    async def get_by_order(self, order_id: int) -> List[Payment]:
        """
        Get all payments for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            List of payment instances for the order
        """
        query = select(Payment).where(Payment.order_id == order_id).order_by(
            Payment.created_at.desc()
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """
        Get payment by external transaction ID.
        
        Args:
            transaction_id: External payment processor transaction ID
            
        Returns:
            Payment instance or None if not found
        """
        query = select(Payment).where(Payment.transaction_id == transaction_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_payments_by_status(
        self, status: PaymentStatus, limit: int = 100, offset: int = 0
    ) -> List[Payment]:
        """
        Get payments by status.
        
        Args:
            status: Payment status to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of payment instances with the specified status
        """
        query = select(Payment).where(
            Payment.status == status
        ).order_by(
            Payment.created_at.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_payments(self, limit: int = 100) -> List[Payment]:
        """
        Get all pending payments awaiting processing.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of pending payment instances
        """
        query = select(Payment).where(
            Payment.status == PaymentStatus.PENDING
        ).order_by(
            Payment.created_at.asc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_completed_payments_for_order(self, order_id: int) -> List[Payment]:
        """
        Get completed payments for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            List of completed payment instances
        """
        query = select(Payment).where(
            Payment.order_id == order_id
        ).where(
            Payment.status == PaymentStatus.COMPLETED
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_total_paid_amount(self, order_id: int) -> float:
        """
        Get total paid amount for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Total paid amount
        """
        from sqlalchemy import func
        query = select(func.sum(Payment.amount)).where(
            Payment.order_id == order_id
        ).where(
            Payment.status == PaymentStatus.COMPLETED
        )
        result = await self.session.execute(query)
        return float(result.scalar() or 0)
