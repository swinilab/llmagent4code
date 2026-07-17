"""
Payment repository for data access operations.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentCreate


class PaymentRepository:
    """
    Repository for Payment entity operations.
    Provides CRUD operations with async support.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get a payment by ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order_id(self, order_id: int) -> Optional[Payment]:
        """Get a payment by order ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: PaymentStatus, skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get payments by status."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get all payments with pagination."""
        result = await self.session.execute(
            select(Payment).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, payment_data: PaymentCreate) -> Payment:
        """Create a new payment."""
        payment = Payment(
            order_id=payment_data.order_id,
            invoice_id=payment_data.invoice_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            method=payment_data.method,
            status=PaymentStatus.PENDING,
            notes=payment_data.notes,
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def update_status(self, payment_id: int, status: PaymentStatus) -> Optional[Payment]:
        """Update payment status."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = status
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def process(self, payment_id: int, transaction_id: Optional[str] = None) -> Optional[Payment]:
        """Mark payment as processing."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentStatus.PROCESSING
        payment.transaction_id = transaction_id
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def complete(self, payment_id: int, transaction_id: Optional[str] = None) -> Optional[Payment]:
        """Mark payment as completed."""
        from datetime import datetime
        
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = transaction_id or payment.transaction_id
        payment.processed_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def fail(self, payment_id: int, notes: Optional[str] = None) -> Optional[Payment]:
        """Mark payment as failed."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentStatus.FAILED
        if notes:
            payment.notes = notes
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def update(self, payment_id: int, **kwargs) -> Optional[Payment]:
        """Update a payment."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        for field, value in kwargs.items():
            setattr(payment, field, value)
        
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
    
    async def delete(self, payment_id: int) -> bool:
        """Delete a payment by ID."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return False
        
        await self.session.delete(payment)
        await self.session.flush()
        return True
    
    async def count(self) -> int:
        """Get total number of payments."""
        result = await self.session.execute(select(func.count()).select_from(Payment))
        return result.scalar() or 0
