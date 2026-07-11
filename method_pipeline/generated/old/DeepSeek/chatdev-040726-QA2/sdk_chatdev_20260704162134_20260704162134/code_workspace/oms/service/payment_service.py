"""
Payment service: processing and verification.
"""

from datetime import datetime, timezone
from uuid import UUID

from oms.domain.enums import OrderStatus, PaymentStatus, InvoiceStatus
from oms.domain.events import PaymentReceived, PaymentVerified
from oms.domain.models import Payment, CreatePaymentRequest
from oms.repository.in_memory import InMemoryPaymentRepository, InMemoryOrderRepository, InMemoryInvoiceRepository
from oms.service.event_bus import event_bus


class PaymentService:
    """Business logic for Payment operations."""

    def __init__(
        self,
        payment_repo: InMemoryPaymentRepository,
        order_repo: InMemoryOrderRepository,
        invoice_repo: InMemoryInvoiceRepository,
    ) -> None:
        self._payment_repo = payment_repo
        self._order_repo = order_repo
        self._invoice_repo = invoice_repo

    def create_payment(self, request: CreatePaymentRequest) -> Payment:
        """Step 4: Customer pays an invoice."""
        order = self._order_repo.find_by_id(request.order_id)
        if order is None:
            raise ValueError(f"Order {request.order_id} not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Order {request.order_id} is in status {order.status.value}, expected invoiced"
            )

        invoice = self._invoice_repo.find_by_id(request.invoice_id)
        if invoice is None:
            raise ValueError(f"Invoice {request.invoice_id} not found")

        # CRITICAL: Validate payment amount matches invoice total
        if request.amount.amount != invoice.total.amount:
            raise ValueError(
                f"Payment amount {request.amount.amount} does not match invoice total {invoice.total.amount}"
            )
        if request.amount.currency != invoice.total.currency:
            raise ValueError(
                f"Payment currency {request.amount.currency} does not match invoice currency {invoice.total.currency}"
            )

        payment = Payment(
            order_id=request.order_id,
            invoice_id=request.invoice_id,
            amount=request.amount,
            method=request.method,
            status=PaymentStatus.PENDING,
        )
        saved = self._payment_repo.save(payment)
        event_bus.publish(PaymentReceived(payment_id=saved.id, order_id=request.order_id, invoice_id=request.invoice_id))
        return saved

    def verify_payment(self, payment_id: UUID, accountant_id: UUID) -> Payment:
        """Step 5: Accountant verifies a payment."""
        payment = self._payment_repo.find_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment {payment_id} is in status {payment.status.value}, expected pending")

        payment.status = PaymentStatus.VERIFIED
        payment.verified_by = accountant_id
        payment.updated_at = datetime.now(timezone.utc)
        saved = self._payment_repo.save(payment)

        # Update order to PAID
        order = self._order_repo.find_by_id(payment.order_id)
        if order is not None:
            order.status = OrderStatus.PAID
            order.updated_at = datetime.now(timezone.utc)
            self._order_repo.save(order)

        # Update invoice to PAID
        invoice = self._invoice_repo.find_by_id(payment.invoice_id)
        if invoice is not None:
            invoice.status = InvoiceStatus.PAID
            invoice.updated_at = datetime.now(timezone.utc)
            self._invoice_repo.save(invoice)

        event_bus.publish(PaymentVerified(payment_id=payment_id, order_id=payment.order_id, accountant_id=accountant_id))
        return saved

    def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Retrieve a payment by ID."""
        return self._payment_repo.find_by_id(payment_id)

    def get_by_order(self, order_id: UUID) -> list[Payment]:
        """List payments for a given order."""
        return self._payment_repo.find_by_order(order_id)

    def list_all(self) -> list[Payment]:
        """List all payments."""
        return self._payment_repo.find_all()
