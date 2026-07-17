"""Payment service for handling payment records."""

from sqlmodel import Session
from typing import Optional

from ..models import Payment, PaymentStatus, Order, OrderStatus

class PaymentService:
    @staticmethod
    def verify_payment(session: Session, payment_id: int) -> Payment:
        payment = session.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError("Payment not completed")
        # Link order status update already done in OrderService.record_payment
        return payment
