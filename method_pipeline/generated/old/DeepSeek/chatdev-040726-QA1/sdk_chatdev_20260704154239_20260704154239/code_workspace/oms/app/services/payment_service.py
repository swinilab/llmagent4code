"""
Service layer for Payment operations.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate


class PaymentStateError(Exception):
    """Raised when an invalid payment state transition is attempted."""


class PaymentService:
    """Business logic for managing payments."""

    @staticmethod
    def create(db: Session, data: PaymentCreate, commit: bool = True) -> Payment:
        payment = Payment(
            order_id=data.order_id,
            amount=data.amount,
            currency=data.currency,
            method=data.method,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        if commit:
            db.commit()
            db.refresh(payment)
        else:
            db.flush()
        return payment

    @staticmethod
    def get_by_id(db: Session, payment_id: str) -> Payment | None:
        return (
            db.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.id == payment_id)
            .first()
        )

    @staticmethod
    def list_by_order(db: Session, order_id: str) -> list[Payment]:
        return (
            db.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.order_id == order_id)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Payment]:
        return (
            db.query(Payment)
            .options(joinedload(Payment.order))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_paid(db: Session, payment_id: str, commit: bool = True) -> Payment | None:
        payment = PaymentService.get_by_id(db, payment_id)
        if not payment:
            return None
        if payment.status != PaymentStatus.PENDING:
            raise PaymentStateError(
                f"Cannot mark payment {payment_id} as paid: current status is {payment.status.value}, "
                f"expected 'pending'"
            )
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
            db.refresh(payment)
        else:
            db.flush()
        return payment

    @staticmethod
    def verify(db: Session, payment_id: str, commit: bool = True) -> Payment | None:
        payment = PaymentService.get_by_id(db, payment_id)
        if not payment:
            return None
        if payment.status != PaymentStatus.PAID:
            raise PaymentStateError(
                f"Cannot verify payment {payment_id}: current status is {payment.status.value}, "
                f"expected 'paid'"
            )
        payment.status = PaymentStatus.VERIFIED
        payment.verified_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
            db.refresh(payment)
        else:
            db.flush()
        return payment

    @staticmethod
    def delete(db: Session, payment_id: str, commit: bool = True) -> bool:
        payment = PaymentService.get_by_id(db, payment_id)
        if not payment:
            return False
        db.delete(payment)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
