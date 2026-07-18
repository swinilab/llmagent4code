"""
Payment repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate


class PaymentRepository:
    """Payment repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, payment: PaymentCreate) -> Payment:
        """Create a new payment."""
        db_payment = Payment(**payment.model_dump())
        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def update_status(self, payment_id: int, status: PaymentStatus) -> Optional[Payment]:
        """Update payment status."""
        db_payment = self.get_by_id(payment_id)
        if db_payment:
            db_payment.status = status
            self.db.commit()
            self.db.refresh(db_payment)
        return db_payment

    def list_by_order(self, order_id: int) -> list[Payment]:
        """List all payments for an order."""
        return self.db.query(Payment).filter(Payment.order_id == order_id).all()