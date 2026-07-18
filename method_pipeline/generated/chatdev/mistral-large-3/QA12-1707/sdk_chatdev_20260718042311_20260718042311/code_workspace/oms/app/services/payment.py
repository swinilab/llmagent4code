"""
Payment service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.payment import PaymentRepository
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentRead


class PaymentService:
    """Payment service."""

    def create_payment(self, payment: PaymentCreate) -> PaymentRead:
        """Create a new payment and log to outbox in a single transaction."""
        try:
            # Create payment (but do not commit yet)
            db_payment = self.repo.create(payment)
            db_payment.is_pending_recovery = True  # Mark for recovery

            # Log to outbox (same transaction)
            from app.models.outbox.outbox import Outbox
            outbox_event = Outbox(
                event_type="PAYMENT_PROCESSED",
                payload={"payment_id": db_payment.id, "order_id": payment.order_id},
                processed=False
            )
            self.repo.db.add(outbox_event)
            self.repo.db.commit()  # Commit both payment and outbox

            return PaymentRead.model_validate(db_payment)
        except Exception as e:
            self.repo.db.rollback()
            logger.error("Failed to create payment", error=str(e))
            raise HTTPException(status_code=500, detail="Payment creation failed")
        if not db_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentRead.model_validate(db_payment)

    def update_payment_status(self, payment_id: int, status: PaymentStatus) -> Optional[PaymentRead]:
        """Update payment status."""
        db_payment = self.repo.update_status(payment_id, status)
        if not db_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentRead.model_validate(db_payment)

    def list_payments_by_order(self, order_id: int) -> list[PaymentRead]:
        """List all payments for an order."""
        db_payments = self.repo.list_by_order(order_id)
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.payment import PaymentRepository
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentRead


class PaymentService:
    """Payment service with workflow logic."""

    def __init__(self, db: Session):
        self.repo = PaymentRepository(db)

    def create_payment(self, payment: PaymentCreate) -> PaymentRead:
        """Create a new payment (Customer)."""
        db_payment = self.repo.create(payment)
        return PaymentRead.model_validate(db_payment)

    def verify_payment(self, payment_id: int) -> PaymentRead:
        """Verify a payment (Accountant)."""
        db_payment = self.repo.update_status(payment_id, PaymentStatus.VERIFIED)
        if not db_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentRead.model_validate(db_payment)

    def get_payment(self, payment_id: int) -> Optional[PaymentRead]:
        """Get payment by ID."""
        db_payment = self.repo.get_by_id(payment_id)
        if not db_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentRead.model_validate(db_payment)

    def update_payment_status(self, payment_id: int, status: PaymentStatus) -> Optional[PaymentRead]:
        """Update payment status."""
        db_payment = self.repo.update_status(payment_id, status)
        if not db_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentRead.model_validate(db_payment)

    def list_payments_by_order(self, order_id: int) -> list[PaymentRead]:
        """List all payments for an order."""
        db_payments = self.repo.list_by_order(order_id)
        return [PaymentRead.model_validate(payment) for payment in db_payments]