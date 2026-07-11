"""
Service layer for Payment entity.
Handles payment creation, verification, and status management.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import PaymentStatus
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate


class PaymentService:
    """Business logic for payment operations."""

    @staticmethod
    async def create(db: AsyncSession, data: PaymentCreate) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            order_id=data.order_id,
            amount=data.amount,
            currency=data.currency,
            method=data.method,
            transaction_ref=data.transaction_ref,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        return payment

    @staticmethod
    async def get_by_id(db: AsyncSession, payment_id: str) -> Optional[Payment]:
        """Retrieve a payment by ID."""
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_order(db: AsyncSession, order_id: str) -> List[Payment]:
        """Get all payments for a given order."""
        result = await db.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Payment]:
        """List payments with pagination."""
        result = await db.execute(
            select(Payment).offset(skip).limit(limit).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def verify_payment(db: AsyncSession, payment_id: str) -> Optional[Payment]:
        """Mark a payment as completed (verification step by Accountant)."""
        payment = await PaymentService.get_by_id(db, payment_id)
        if not payment:
            return None
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment {payment_id} is already in status {payment.status.value}")

        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.now(timezone.utc)
        await db.flush()
        # Refresh to load server-side defaults (updated_at)
        await db.refresh(payment)
        return payment

    @staticmethod
    async def update(db: AsyncSession, payment_id: str, data: PaymentUpdate) -> Optional[Payment]:
        """Update payment fields."""
        payment = await PaymentService.get_by_id(db, payment_id)
        if not payment:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(payment, field, value)
        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def delete(db: AsyncSession, payment_id: str) -> bool:
        """Delete a payment by ID."""
        payment = await PaymentService.get_by_id(db, payment_id)
        if not payment:
            return False
        await db.delete(payment)
        await db.flush()
        return True
