"""
PaymentService — processes payments with circuit breaker protection.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.core.config import get_settings
from oms_backend.models.orm_models import Invoice, Order, Payment
from oms_backend.repositories.entities import InvoiceRepository, OrderRepository, PaymentRepository
from oms_backend.schemas.domain import InvoiceStatus, PaymentCreate, PaymentStatus, PaymentWebhookPayload
from oms_backend.services.utils import audit_log


class CircuitBreaker:
    """Simple in-memory circuit breaker per service instance."""

    def __init__(self, threshold: int = 5, timeout_seconds: int = 30):
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time: datetime | None = None
        self.state: str = "closed"  # closed | open | half-open"

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        if self.failures >= self.threshold:
            self.state = "open"

    def is_open(self) -> bool:
        if self.state == "open" and self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed >= self.timeout_seconds:
                self.state = "half-open"
                return False
            return True
        return False


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        cfg = get_settings().payment_gateway
        self.circuit_breaker = CircuitBreaker(
            threshold=cfg.circuit_breaker_threshold,
            timeout_seconds=cfg.circuit_breaker_timeout_seconds,
        )

    async def authorize_and_capture(self, data: PaymentCreate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Payment:
        """
        Two-step: authorize on gateway, then capture.
        Simulated here — replace with real gateway SDK calls.
        """
        if self.circuit_breaker.is_open():
            raise RuntimeError("Payment gateway circuit breaker is open; service unavailable")

        invoice = await self.invoice_repo.get_with_relations(data.invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {data.invoice_id} not found")
        if invoice.status != "issued":
            raise ValueError(f"Invoice {invoice.code} is {invoice.status}; can only pay issued invoices")

        # Verify amount matches
        if data.amount != invoice.total_amount:
            raise ValueError(f"Payment amount {data.amount} does not match invoice total {invoice.total_amount}")

        # Generate payment record
        code = await self.payment_repo.next_code()

        try:
            # ── Simulate gateway authorization ────────────────────────────────
            # In production: gateway.authorize(amount=data.amount, currency=data.currency, reference=...)
            gateway_reference = f"gw_{uuid.uuid4().hex[:16]}"
            # ──────────────────────────────────────────────────────────────────

            payment = await self.payment_repo.create(
                code=code,
                invoice_id=data.invoice_id,
                order_id=invoice.order_id,
                customer_id=invoice.customer_id,
                amount=data.amount,
                currency=data.currency,
                status=PaymentStatus.AUTHORIZED.value,
                method=data.method,
                reference=gateway_reference,
                gateway=data.gateway or "simulated",
                authorized_at=datetime.utcnow(),
                created_by=actor_id,
            )

            # Capture immediately (simplified; real gateway would do separate capture)
            await self.payment_repo.update(
                payment.id,
                status=PaymentStatus.CAPTURED.value,
                captured_at=datetime.utcnow(),
            )
            self.circuit_breaker.record_success()

            # Advance invoice and order to PAID to unblock workflow step 6 (ship)
            await self.invoice_repo.update(
                invoice.id,
                status=InvoiceStatus.PAID.value,
                paid_date=datetime.utcnow().date(),
            )
            await self.order_repo.update_status(invoice.order_id, "paid")

        except Exception as exc:
            self.circuit_breaker.record_failure()
            # Record failed payment
            code = await self.payment_repo.next_code()
            await self.payment_repo.create(
                code=code,
                invoice_id=data.invoice_id,
                order_id=invoice.order_id,
                customer_id=invoice.customer_id,
                amount=data.amount,
                currency=data.currency,
                status=PaymentStatus.FAILED.value,
                method=data.method,
                gateway=data.gateway or "simulated",
                failed_at=datetime.utcnow(),
                created_by=actor_id,
            )
            raise RuntimeError(f"Payment gateway error: {exc}") from exc

        # Reload full payment
        await self.session.refresh(payment)
        await audit_log(self.session, "payment", payment.id, "captured",
                        actor_id=actor_id,
                        payload={"amount": str(data.amount), "gateway_ref": gateway_reference},
                        ip_address=ip_address)

        return payment

    async def handle_webhook(self, payload: PaymentWebhookPayload, ip_address: str | None = None) -> Payment | None:
        """
        Process payment gateway webhook to update payment status.
        """
        payment = await self.payment_repo.get_by_reference(payload.reference)
        if not payment:
            return None

        status_map = {
            PaymentStatus.AUTHORIZED.value: "authorized_at",
            PaymentStatus.CAPTURED.value:   "captured_at",
            PaymentStatus.FAILED.value:     "failed_at",
            PaymentStatus.REFUNDED.value:   "refunded_at",
        }

        update_data: dict[str, Any] = {"status": payload.status.value}
        ts_field = status_map.get(payload.status.value)
        if ts_field:
            update_data[ts_field] = datetime.utcnow()

        await self.payment_repo.update(payment.id, **update_data)
        await self.session.refresh(payment)

        await audit_log(self.session, "payment", payment.id, f"webhook_{payload.status.value}",
                        payload={"reference": payload.reference}, ip_address=ip_address)

        return payment

    async def refund(self, id: uuid.UUID, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Payment | None:
        """Refund a captured payment."""
        payment = await self.payment_repo.get(id)
        if not payment:
            return None
        if payment.status != PaymentStatus.CAPTURED.value:
            raise ValueError(f"Cannot refund payment {payment.code} in {payment.status} status")

        # Simulate gateway refund call
        # In production: gateway.refund(reference=payment.reference)
        updated = await self.payment_repo.update(
            id,
            status=PaymentStatus.REFUNDED.value,
            refunded_at=datetime.utcnow(),
        )
        if updated:
            await audit_log(self.session, "payment", id, "refunded", actor_id=actor_id, ip_address=ip_address)
        return await self.payment_repo.get(id)

    async def get(self, id: uuid.UUID) -> Payment | None:
        return await self.payment_repo.get(id)

    async def list_by_invoice(self, invoice_id: uuid.UUID) -> list[Payment]:
        return await self.payment_repo.get_by_invoice(invoice_id)

    async def list_all(self, page: int = 1, page_size: int = 20) -> tuple[list[Payment], int]:
        return await self.payment_repo.list_all(page=page, page_size=page_size, order_by="created_at", descending=True)
