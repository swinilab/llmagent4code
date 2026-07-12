"""
OMS Payment Service - Business logic for payment processing.
"""
from typing import List, Optional
import uuid
from datetime import datetime
from decimal import Decimal
from app.domain.entities.models import Payment, PaymentStatus, PaymentMethod, Money, Currency
from app.domain.repositories.interfaces import PaymentRepository


class PaymentService:
    """Service for payment operations."""

    def __init__(self, payment_repo: PaymentRepository):
        self._repo = payment_repo

    def create_payment(
        self,
        order_id: str,
        customer_id: str,
        amount: Money,
        method: PaymentMethod = PaymentMethod.BANK_TRANSFER,
        metadata: Optional[dict] = None
    ) -> Payment:
        """Create a new payment."""
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            amount=amount,
            status=PaymentStatus.PENDING,
            method=method,
            metadata=metadata
        )
        return self._repo.save(payment)

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return self._repo.find_by_id(payment_id)

    def get_payments_for_order(self, order_id: str) -> List[Payment]:
        """Get all payments for an order."""
        return self._repo.find_by_order(order_id)

    def get_payments_by_status(self, status: PaymentStatus) -> List[Payment]:
        """Get payments by status."""
        return self._repo.find_by_status(status)

    def complete_payment(self, payment_id: str, transaction_ref: str) -> Optional[Payment]:
        """Mark payment as completed with transaction reference."""
        payment = self._repo.find_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None
        
        return self._repo.update(payment_id, {
            'status': PaymentStatus.COMPLETED,
            'transaction_ref': transaction_ref,
            'processed_at': datetime.utcnow()
        })

    def fail_payment(self, payment_id: str, reason: str) -> Optional[Payment]:
        """Mark payment as failed with reason."""
        payment = self._repo.find_by_id(payment_id)
        if not payment or payment.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            return None
        
        return self._repo.update(payment_id, {
            'status': PaymentStatus.FAILED,
            'failure_reason': reason,
            'processed_at': datetime.utcnow()
        })

    def process_payment(self, payment_id: str) -> Optional[Payment]:
        """Mark payment as processing."""
        payment = self._repo.find_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None
        
        return self._repo.update(payment_id, {
            'status': PaymentStatus.PROCESSING
        })

    def refund_payment(self, payment_id: str) -> Optional[Payment]:
        """Refund a completed payment."""
        payment = self._repo.find_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.COMPLETED:
            return None
        
        return self._repo.update(payment_id, {
            'status': PaymentStatus.REFUNDED,
            'processed_at': datetime.utcnow()
        })
