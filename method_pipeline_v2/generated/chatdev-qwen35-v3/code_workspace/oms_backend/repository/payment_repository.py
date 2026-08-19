"""
Payment repository with CRUD operations
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.domain.models import Payment, PaymentStatus, PaymentMethod
from oms_backend.domain.schemas import PaymentCreate


class PaymentRepository:
    """Repository for Payment entity operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: PaymentCreate) -> Payment:
        """Create a new payment"""
        payment = Payment(
            order_ref=data.orderRef,
            amount=data.amount,
            status=PaymentStatus.PENDING,
            method=data.method
        )
        self.session.add(payment)
        await self.session.flush()
        return payment
    
    async def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order_ref(self, order_ref: str) -> List[Payment]:
        """Get all payments for an order"""
        result = await self.session.execute(
            select(Payment).where(Payment.order_ref == order_ref)
        )
        return result.scalars().all()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Payment]:
        """Get all payments with pagination"""
        result = await self.session.execute(
            select(Payment).offset(offset).limit(limit)
        )
        return result.scalars().all()
    
    async def update_status(self, payment_id: str, new_status: PaymentStatus) -> Optional[Payment]:
        """Update payment status"""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        # State machine validation
        valid_transitions = {
            PaymentStatus.PENDING: [PaymentStatus.VERIFIED, PaymentStatus.REJECTED],
            PaymentStatus.VERIFIED: [],
            PaymentStatus.REJECTED: [PaymentStatus.PENDING],
        }
        
        if new_status not in valid_transitions.get(payment.status, []):
            raise ValueError(f"Invalid status transition from {payment.status} to {new_status}")
        
        payment.status = new_status
        await self.session.flush()
        return payment
    
    async def update(self, payment_id: str, data: dict) -> Optional[Payment]:
        """Update payment fields"""
        await self.session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(**data)
        )
        return await self.get_by_id(payment_id)
    
    async def delete(self, payment_id: str) -> bool:
        """Delete payment"""
        payment = await self.get_by_id(payment_id)
        if payment:
            await self.session.delete(payment)
            return True
        return False
