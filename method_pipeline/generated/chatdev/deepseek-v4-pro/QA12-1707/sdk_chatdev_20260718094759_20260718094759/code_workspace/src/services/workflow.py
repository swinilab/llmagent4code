"""
Workflow orchestration service — implements the 7-step OMS workflow.

ADR-005: Centralised workflow service for cross-entity orchestration.
  Decision: A dedicated WorkflowService that coordinates Order, Invoice, Payment services.
  Context: NFR 1.1 (Response Time) — single service call for multi-step transitions
    reduces round-trips; NFR 2.3 (State Preservation) — transactional boundaries
    ensure consistency.
  Alternatives: (a) choreography via events — harder to reason about;
    (b) saga pattern — overkill for single-database system.
  Consequences: WorkflowService becomes a god object if not carefully maintained;
    mitigated by delegating to entity services.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import OrderStatus
from src.services.invoice import InvoiceService
from src.services.order import OrderService
from src.services.payment import PaymentService
from src.utils.exceptions import ConflictError


class WorkflowService:
    """
    Implements the full OMS workflow:

    1. Customer places order          → OrderService.create
    2. Order Staff reviews & accepts  → transition to ACCEPTED
    3. Accountant creates invoice     → InvoiceService.create + transition to INVOICED
    4. Customer pays invoice          → PaymentService.create
    5. Accountant verifies payment    → PaymentService.verify + transition to PAID
    6. Order Staff ships order        → transition to SHIPPED
    7. Order Staff closes order       → transition to CLOSED
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_svc = OrderService(session)
        self.invoice_svc = InvoiceService(session)
        self.payment_svc = PaymentService(session)

    # ── Step 2: Staff accepts order ────────────────────────
    async def staff_accept_order(self, order_id: str) -> dict:
        """Staff reviews and accepts a pending order."""
        order = await self.order_svc.transition_status(order_id, OrderStatus.ACCEPTED.value)
        return {"order_id": order.id, "status": order.status.value}

    # ── Step 3: Accountant creates invoice ─────────────────
    async def accountant_create_invoice(
        self, order_id: str, billing_info: str, due_date=None
    ) -> dict:
        """Create invoice for an accepted order and transition to INVOICED."""
        order = await self.order_svc.get(order_id)
        if order.status != OrderStatus.ACCEPTED:
            raise ConflictError(
                f"Order must be accepted before invoicing. Current: {order.status.value}"
            )

        from src.schemas.invoice import InvoiceCreate

        payload = InvoiceCreate(
            order_id=order_id,
            billing_info=billing_info,
            due_date=due_date,
        )
        invoice = await self.invoice_svc.create(
            payload, order.subtotal, order.tax, order.total
        )
        await self.order_svc.set_invoice_id(order_id, invoice.id)
        await self.order_svc.transition_status(order_id, OrderStatus.INVOICED.value)
        return {
            "invoice_id": invoice.id,
            "order_id": order.id,
            "total": str(invoice.total),
            "status": invoice.status.value,
        }

    # ── Step 4: Customer pays ──────────────────────────────
    async def customer_pay(self, order_id: str, amount, method: str = "bank_transfer") -> dict:
        """Customer submits payment for an invoiced order."""
        order = await self.order_svc.get(order_id)
        if order.status != OrderStatus.INVOICED:
            raise ConflictError(
                f"Order must be invoiced before payment. Current: {order.status.value}"
            )

        from src.schemas.payment import PaymentCreate

        payload = PaymentCreate(order_id=order_id, amount=amount, method=method)
        payment = await self.payment_svc.create(payload)
        return {
            "payment_id": payment.id,
            "order_id": order.id,
            "amount": str(payment.amount),
            "status": payment.status.value,
        }

    # ── Step 5: Accountant verifies payment ────────────────
    async def accountant_verify_payment(self, payment_id: str) -> dict:
        """Accountant verifies payment and transitions order to PAID."""
        payment = await self.payment_svc.verify(payment_id, "completed")
        order = await self.order_svc.get(payment.order_id)
        if order.status != OrderStatus.INVOICED:
            raise ConflictError(
                f"Order must be invoiced. Current: {order.status.value}"
            )
        await self.order_svc.transition_status(order.id, OrderStatus.PAID.value)
        if order.invoice_id:
            await self.invoice_svc.mark_paid(order.invoice_id)
        return {
            "payment_id": payment.id,
            "order_id": order.id,
            "payment_status": payment.status.value,
            "order_status": OrderStatus.PAID.value,
        }

    # ── Step 6: Staff ships order ──────────────────────────
    async def staff_ship_order(self, order_id: str) -> dict:
        """Staff ships a paid order."""
        order = await self.order_svc.transition_status(order_id, OrderStatus.SHIPPED.value)
        return {"order_id": order.id, "status": order.status.value}

    # ── Step 7: Staff closes order ─────────────────────────
    async def staff_close_order(self, order_id: str) -> dict:
        """Staff closes a shipped order."""
        order = await self.order_svc.transition_status(order_id, OrderStatus.CLOSED.value)
        return {"order_id": order.id, "status": order.status.value}
