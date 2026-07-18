"""
Payment service — business logic for payment processing and verification.

Implements steps 4 and 5 of the workflow:
  4. Customer pays invoice (creates a PENDING payment)
  5. Accountant verifies payment (transitions to VERIFIED or FAILED,
     and if verified, transitions the order to PAID and the invoice to PAID)

Uses a circuit breaker around the "payment gateway" call to satisfy
NFR 2.2 (Fault Detection and Recovery).
"""
import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from oms.core.resilience import with_circuit_breaker, CircuitBreakerOpenError
from oms.enums import OrderStatus, PaymentStatus, InvoiceStatus
from oms.models.order import Order
from oms.models.payment import Payment
from oms.repositories.invoice import InvoiceRepository
from oms.repositories.order import OrderRepository
from oms.repositories.payment import PaymentRepository
from oms.schemas.order import OrderStatusUpdate
from oms.schemas.payment import PaymentCreate, PaymentVerify
from oms.services.order import OrderTransitionError, OrderService

logger = logging.getLogger(__name__)

class PaymentError(Exception):
    """Raised when a payment operation fails business validation."""
    pass


class PaymentService:
    """Business logic for Payment entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentRepository(session)
        self.order_repo = OrderRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.order_service = OrderService(session)

    async def _validate_payment_gateway(self, amount: float, method: str) -> bool:
        """
        Simulated payment gateway validation.

        In production this would call an external PSP. Here we simply
        validate that the amount is positive. The circuit breaker
        protects against repeated gateway failures.
        """
        if amount <= 0:
            return False
        return True

    async def create_payment(self, data: PaymentCreate) -> Payment:
        """
        Create a payment for an order's invoice.

        The order must be in INVOICED status and have an associated invoice.
        The payment amount must match the invoice total.
        """
        order = await self.order_repo.get_full(data.order_id)
        if order is None:
            raise PaymentError(f"Order {data.order_id} not found")

        if order.status != OrderStatus.INVOICED:
            raise PaymentError(
                f"Order must be INVOICED to receive payment (current: {order.status.value})"
            )

        if order.invoice is None:
            raise PaymentError(f"Order {data.order_id} has no invoice")

        invoice = order.invoice
        if abs(float(data.amount) - float(invoice.total)) > 0.01:
            raise PaymentError(
                f"Payment amount {data.amount} does not match invoice total {invoice.total}"
            )

        # Simulate payment gateway call through circuit breaker (NFR 2.2)
        @with_circuit_breaker("payment_gateway")
        async def _gateway_call() -> bool:
            return await self._validate_payment_gateway(float(data.amount), data.method.value)

        gateway_ok = False
        try:
            gateway_ok = await _gateway_call()
        except CircuitBreakerOpenError:
            raise PaymentError(
                "Payment gateway is temporarily unavailable (circuit open). "
                "Please retry shortly."
            )

        status = PaymentStatus.PENDING if gateway_ok else PaymentStatus.FAILED

        payment = await self.repo.create(
            order_id=data.order_id,
            amount=float(data.amount),
            status=status,
            method=data.method,
        )
        await self.session.commit()
        logger.info(
            "Created payment %s for order %s (status=%s)",
            payment.id, data.order_id, status.value,
        )
        return payment

    async def verify_payment(self, payment_id: str, data: PaymentVerify) -> Payment | None:
        """
        Verify or reject a payment (Accountant action, step 5).

        If verified, transitions the associated order to PAID and the
        invoice to PAID status.  All three writes (payment → VERIFIED,
        order → PAID, invoice → PAID) are performed within a single
        transaction so that either they all commit together or none do,
        preventing the order being PAID while the invoice stays ISSUED.
        """
        payment = await self.repo.get_by_id(payment_id)
        if payment is None:
            return None

        if payment.status != PaymentStatus.PENDING:
            raise PaymentError(
                f"Payment already processed (status: {payment.status.value})"
            )

        if data.verified:
            payment = await self.repo.update(payment, status=PaymentStatus.VERIFIED)
            # Transition order to PAID (defer commit so the invoice update
            # is part of the same atomic transaction).
            order = await self.order_repo.get_full(payment.order_id)
            if order is not None and order.status == OrderStatus.INVOICED:
                await self.order_service.transition_status(
                    order.id,
                    OrderStatusUpdate(
                        status=OrderStatus.PAID,
                        reason="Payment verified",
                    ),
                    commit=False,
                )
                # Mark the associated invoice as PAID so it is not
                # later flagged OVERDUE by the cron job.
                if order.invoice is not None:
                    await self.invoice_repo.update(
                        order.invoice, status=InvoiceStatus.PAID,
                    )
        else:
            payment = await self.repo.update(payment, status=PaymentStatus.FAILED)

        # Single atomic commit for payment + order + invoice.
        await self.session.commit()
        await self.session.refresh(payment)
        logger.info("Payment %s verified=%s", payment_id, data.verified)
        return payment

    async def get_payment(self, payment_id: str) -> Payment | None:
        """Fetch a payment by ID."""
        return await self.repo.get_by_id(payment_id)

    async def list_payments_by_order(self, order_id: str) -> Sequence[Payment]:
        """List all payments for an order."""
        return await self.repo.get_by_order(order_id)

    async def list_payments(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[Sequence[Payment], int]:
        """List all payments with pagination."""
        offset = (page - 1) * page_size
        return await self.repo.get_all(offset=offset, limit=page_size)