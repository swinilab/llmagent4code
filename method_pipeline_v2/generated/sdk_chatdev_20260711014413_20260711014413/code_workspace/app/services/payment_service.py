"""
Payment service — process and verify payments.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.infrastructure.circuit_breaker import CircuitBreaker
from app.models.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment_schema import PaymentResponse


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        order_repo: OrderRepository,
        invoice_repo: InvoiceRepository,
    ) -> None:
        self._payment_repo = payment_repo
        self._order_repo = order_repo
        self._invoice_repo = invoice_repo
        self._gateway_cb = CircuitBreaker(name="payment-gateway")

    async def process_payment(
        self,
        order_id: str,
        amount: float,
        currency: str,
        method: PaymentMethod,
    ) -> PaymentResponse:
        """Customer pays invoice (step 4)."""
        order = await self._order_repo.get(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(f"Cannot pay order in status {order.status.value}")

        # Validate payment amount matches order total
        if abs(amount - order.total_amount) > 0.01:
            raise ValueError(
                f"Payment amount {amount} does not match order total {order.total_amount}"
            )

        # Check for existing payment on this order
        existing = await self._payment_repo.get_by_order(order_id)
        if existing is not None:
            raise ValueError(f"Order {order_id} already has a payment ({existing.id})")

        # Simulate payment gateway call through circuit breaker
        transaction_id = await self._gateway_cb.call(
            self._simulate_gateway_call, order_id, amount, currency, method
        )

        payment = await self._payment_repo.create(
            order_id=order_id,
            amount=amount,
            currency=currency,
            method=method,
            status=PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
        )

        order.status = OrderStatus.PAID

        # Update the associated invoice to reflect payment
        invoice = await self._invoice_repo.get_by_order(order_id)
        if invoice:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(timezone.utc)

        await self._order_repo.session.flush()

        return PaymentResponse.model_validate(payment)

    async def verify_payment(self, payment_id: str) -> PaymentResponse:
        """Accountant verifies payment (step 5)."""
        payment = await self._payment_repo.get(payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Payment is in status {payment.status.value}, cannot verify")

        # Ensure the associated invoice is also marked as paid
        invoice = await self._invoice_repo.get_by_order(payment.order_id)
        if invoice and invoice.status != InvoiceStatus.PAID:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(timezone.utc)
            await self._payment_repo.session.flush()

        return PaymentResponse.model_validate(payment)

    async def get_payment(self, payment_id: str) -> PaymentResponse | None:
        payment = await self._payment_repo.get(payment_id)
        if payment is None:
            return None
        return PaymentResponse.model_validate(payment)

    async def list_payments(
        self,
        status: PaymentStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PaymentResponse], int]:
        payments, total = await self._payment_repo.list_by_status(
            status=status, skip=skip, limit=limit
        )
        return [PaymentResponse.model_validate(p) for p in payments], total

    async def _simulate_gateway_call(
        self,
        order_id: str,
        amount: float,
        currency: str,
        method: PaymentMethod,
    ) -> str:
        """Simulate an external payment gateway call."""
        # In production this would be an HTTP call to a payment provider
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"
