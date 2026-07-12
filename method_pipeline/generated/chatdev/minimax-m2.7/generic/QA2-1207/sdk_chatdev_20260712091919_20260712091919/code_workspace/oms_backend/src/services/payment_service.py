"""
Payment Service - business logic for payment processing.
Handles: create payment -> process -> verify workflow.
"""
import logging
import random
import string
import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from ..domain.models import Payment, PaymentStatus, Invoice, InvoiceStatus, Order, OrderStatus
from ..infrastructure.repositories import PaymentRepository, InvoiceRepository, OrderRepository
from ..utils.resilience import CircuitBreaker, CircuitBreakerConfig, with_retry, FeatureFlags

logger = logging.getLogger(__name__)


class PaymentProcessingError(Exception):
    """Raised when payment processing fails."""
    pass


class PaymentService:
    """
    Service layer for payment operations.
    Step 4 in workflow: Customer pays invoice.
    Step 5: Accountant verifies payment.
    """

    def __init__(self, db_session=None, feature_flags: Optional[FeatureFlags] = None):
        self.db_session = db_session
        self._repo = None
        self._invoice_repo = None
        self._order_repo = None
        self._feature_flags = feature_flags or FeatureFlags()
        self._payment_circuit_breaker = CircuitBreaker(
            "payment_processing",
            CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
        )

    @property
    def repo(self) -> PaymentRepository:
        if self._repo is None:
            if self.db_session:
                self._repo = PaymentRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._repo

    @property
    def invoice_repo(self) -> InvoiceRepository:
        if self._invoice_repo is None:
            if self.db_session:
                self._invoice_repo = InvoiceRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._invoice_repo

    @property
    def order_repo(self) -> OrderRepository:
        if self._order_repo is None:
            if self.db_session:
                self._order_repo = OrderRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._order_repo

    def _generate_transaction_ref(self) -> str:
        """Generate a unique transaction reference."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"TXN-{timestamp}-{random_chars}"

    def create_payment(self, order_id: str, invoice_id: str, customer_id: str,
                      amount: float, method: str = "bank_transfer",
                      idempotency_key: Optional[str] = None) -> Payment:
        """
        Step 4: Create a payment for an invoice.
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise PaymentProcessingError(f"Invoice not found: {invoice_id}")

        if invoice.status not in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            raise PaymentProcessingError(
                f"Cannot pay invoice in status: {invoice.status}. Expected: issued or overdue"
            )

        if abs(amount - invoice.total) > 0.01:
            raise PaymentProcessingError(
                f"Payment amount {amount} does not match invoice total {invoice.total}"
            )

        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise PaymentProcessingError(f"Order not found: {order_id}")

        payment = Payment(
            order_id=order_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=amount,
            currency=invoice.currency,
            method=method,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key
        )

        if idempotency_key:
            saved_payment, created = self.repo.create_with_idempotency(payment)
            if not created:
                logger.info(f"Returning existing payment for idempotency key: {idempotency_key}")
                return saved_payment
        else:
            saved_payment = self.repo.create(payment)

        logger.info(f"Payment created: {saved_payment.id} for invoice: {invoice_id}")
        return saved_payment

    @with_retry(max_attempts=3, backoff_factor=0.5)
    def process_payment(self, payment_id: str) -> Payment:
        """
        Process a payment (simulate payment gateway call).
        Uses circuit breaker and retry for resilience.
        """
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise PaymentProcessingError(f"Payment not found: {payment_id}")

        if payment.status != PaymentStatus.PENDING:
            raise PaymentProcessingError(
                f"Cannot process payment in status: {payment.status}. Expected: pending"
            )

        payment.status = PaymentStatus.PROCESSING
        payment = self.repo.update(payment)

        try:
            if not self._payment_circuit_breaker.allow_request():
                logger.warning(f"Circuit breaker open for payment processing")
                payment.status = PaymentStatus.FAILED
                payment.transaction_ref = "CIRCUIT_OPEN"
                return self.repo.update(payment)

            success = self._simulate_payment_gateway(payment)

            if success:
                payment.status = PaymentStatus.COMPLETED
                payment.transaction_ref = self._generate_transaction_ref()
                payment.processed_at = datetime.now(timezone.utc)
                self._payment_circuit_breaker.record_success()
            else:
                payment.status = PaymentStatus.FAILED
                payment.transaction_ref = "DECLINED"
                self._payment_circuit_breaker.record_failure()

            updated_payment = self.repo.update(payment)
            logger.info(f"Payment processed: {payment_id}, status: {updated_payment.status}")
            return updated_payment

        except Exception as e:
            self._payment_circuit_breaker.record_failure()
            payment.status = PaymentStatus.FAILED
            payment.transaction_ref = f"ERROR: {str(e)[:50]}"
            self.repo.update(payment)
            raise PaymentProcessingError(f"Payment processing failed: {e}")

    def _simulate_payment_gateway(self, payment: Payment) -> bool:
        """
        Simulate payment gateway call.
        In production, this would call actual payment provider.
        """
        time.sleep(0.1)
        return True

    def verify_payment(self, payment_id: str) -> Payment:
        """
        Step 5: Accountant verifies payment.
        Idempotent - safe to call multiple times.
        """
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise PaymentProcessingError(f"Payment not found: {payment_id}")

        if payment.status != PaymentStatus.COMPLETED:
            raise PaymentProcessingError(
                f"Cannot verify payment in status: {payment.status}. Expected: completed"
            )

        invoice = self.invoice_repo.get_by_id(payment.invoice_id)
        if not invoice:
            raise PaymentProcessingError(f"Invoice not found: {payment.invoice_id}")

        # Idempotency: If already verified (invoice already PAID), return early
        if invoice.status == InvoiceStatus.PAID:
            logger.info(f"Payment {payment_id} already verified, invoice already paid")
            return payment

        invoice.status = InvoiceStatus.PAID
        invoice.paid_date = datetime.now(timezone.utc)
        self.invoice_repo.update(invoice)

        # Update order status to PAID as per workflow Step 5
        order = self.order_repo.get_by_id(payment.order_id)
        if order:
            order_status = order.status.value if hasattr(order.status, 'value') else order.status
            if order_status == "invoiced":
                order.status = OrderStatus.PAID
                self.order_repo.update(order)
                logger.info(f"Order {order.id} marked as paid after payment verification")
        order = self.order_repo.get_by_id(payment.order_id)
        if order:
            order_status = order.status.value if hasattr(order.status, 'value') else order.status
            if order_status == "invoiced":
                order.status = OrderStatus.PAID
                self.order_repo.update(order)
                logger.info(f"Order {order.id} marked as paid after payment verification")

        logger.info(f"Payment verified: {payment_id}")
        return payment

    def refund_payment(self, payment_id: str, reason: str = "") -> Payment:
        """Refund a completed payment."""
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise PaymentProcessingError(f"Payment not found: {payment_id}")

        if payment.status != PaymentStatus.COMPLETED:
            raise PaymentProcessingError(
                f"Cannot refund payment in status: {payment.status}. Expected: completed"
            )

        payment.status = PaymentStatus.REFUNDED
        updated_payment = self.repo.update(payment)

        logger.info(f"Payment refunded: {payment_id}, reason: {reason}")
        return updated_payment

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return self.repo.get_by_id(payment_id)

    def get_payments_by_order(self, order_id: str) -> List[Payment]:
        """Get all payments for an order."""
        return self.repo.get_by_order(order_id)

    def get_payments_by_invoice(self, invoice_id: str) -> List[Payment]:
        """Get all payments for an invoice."""
        return self.repo.get_by_invoice(invoice_id)


def get_payment_service(db_session=None) -> PaymentService:
    """Factory function to get payment service."""
    return PaymentService(db_session)
