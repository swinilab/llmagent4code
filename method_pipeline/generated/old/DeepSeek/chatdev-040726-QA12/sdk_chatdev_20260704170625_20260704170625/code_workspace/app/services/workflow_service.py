"""Workflow Orchestrator — ties together the 7-step order lifecycle.

This service coordinates cross-cutting concerns across multiple domain services
to enforce the correct order lifecycle transitions. Heavy operations are
offloaded to the async queue (NFR 1.3).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    Invoice,
    InvoiceStatus,
    LineItem,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    utcnow,
)
from app.middleware.queue_manager import QueueTask, queue_manager
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


class WorkflowError(Exception):
    """Raised when a workflow step violates business rules.

    Triggers a transaction rollback via get_db dependency.
    """


class WorkflowService:
    """Orchestrates the complete order workflow.

    Each method corresponds to one step in the lifecycle and updates
    the relevant domain objects atomically. Heavy operations are
    offloaded to the async queue (NFR 1.3).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_svc = OrderService(session)
        self._invoice_svc = InvoiceService(session)
        self._payment_svc = PaymentService(session)

    # ── Step 1: Customer places order ─────────────────────────────────────────
    async def place_order(
        self, customer_id: str, line_items: list[LineItem]
    ) -> Order:
        order = await self._order_svc.place_order(customer_id, line_items)

        # Offload notification to async queue (NFR 1.3)
        await queue_manager.submit(QueueTask(
            name="order_placed_notification",
            payload={"order_id": order.id, "customer_id": customer_id},
        ))
        return order

    # ── Step 2: Order Staff reviews & accepts ─────────────────────────────────
    async def accept_order(self, order_id: str) -> Optional[Order]:
        order = await self._order_svc.accept_order(order_id)
        if order:
            await queue_manager.submit(QueueTask(
                name="order_accepted_notification",
                payload={"order_id": order_id},
            ))
        return order

    # ── Step 3: Accountant creates invoice ────────────────────────────────────
    async def create_invoice(
        self,
        order_id: str,
        customer_id: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        due_days: int = 30,
    ) -> Optional[Invoice]:
        # First validate the order is in ACCEPTED state
        order = await self._order_svc.get_order(order_id)
        if order is None or order.status != OrderStatus.ACCEPTED:
            return None

        invoice = await self._invoice_svc.create_invoice(
            order_id=order_id,
            customer_id=customer_id,
            billing_name=billing_name,
            billing_address=billing_address,
            total_amount=total_amount,
            due_days=due_days,
        )

        # Mark order as INVOICED
        updated = await self._order_svc.mark_invoiced(order_id, invoice.id)
        if updated is None:
            return None

        # Offload invoice generation task to async queue (NFR 1.3)
        await queue_manager.submit(QueueTask(
            name="invoice_generated",
            payload={"invoice_id": invoice.id, "order_id": order_id},
        ))
        return invoice

    # ── Step 4: Customer pays invoice ─────────────────────────────────────────
    async def pay_invoice(self, invoice_id: str) -> Invoice:
        """Pay an invoice and update the associated order.

        Validates that at least one Payment record exists for this invoice
        before marking anything as paid, ensuring an audit trail (NFR 1.2).

        Both operations happen within the same request's transaction.
        If the order status transition fails, a WorkflowError is raised,
        which triggers a transaction rollback via the get_db dependency.
        """
        # Validate that a payment record exists for this invoice
        payments = await self._payment_svc.get_by_invoice(invoice_id)
        if not payments:
            raise WorkflowError(
                f"No payment record found for invoice {invoice_id}. "
                "Create a payment first."
            )

        invoice = await self._invoice_svc.mark_paid(invoice_id)
        if invoice is None:
            raise WorkflowError("Invoice cannot be paid (must be ISSUED/OVERDUE)")

        # Mark order as PAID via OrderService
        updated = await self._order_svc.mark_paid(invoice.order_id)
        if updated is None:
            raise WorkflowError(
                f"Order {invoice.order_id} cannot be marked PAID (must be INVOICED)"
            )

        await queue_manager.submit(QueueTask(
            name="payment_received",
            payload={"invoice_id": invoice_id, "order_id": invoice.order_id},
        ))
        return invoice

    # ── Step 5: Accountant verifies payment ───────────────────────────────────
    async def verify_payment(self, payment_id: str) -> Payment:
        payment = await self._payment_svc.complete_payment(payment_id)
        if payment is None:
            raise WorkflowError("Payment cannot be completed (must be PENDING)")

        # Mark order as VERIFIED
        updated = await self._order_svc.mark_verified(payment.order_id)
        if updated is None:
            raise WorkflowError(
                f"Order {payment.order_id} cannot be marked VERIFIED (must be PAID)"
            )

        await queue_manager.submit(QueueTask(
            name="payment_verified",
            payload={"payment_id": payment_id, "order_id": payment.order_id},
        ))
        return payment

    # ── Step 6: Order Staff ships paid order ──────────────────────────────────
    async def ship_order(self, order_id: str) -> Optional[Order]:
        order = await self._order_svc.ship_order(order_id)
        if order:
            await queue_manager.submit(QueueTask(
                name="order_shipped",
                payload={"order_id": order_id},
            ))
        return order

    # ── Step 7: Order Staff closes completed order ────────────────────────────
    async def close_order(self, order_id: str) -> Optional[Order]:
        order = await self._order_svc.close_order(order_id)
        if order:
            await queue_manager.submit(QueueTask(
                name="order_closed",
                payload={"order_id": order_id},
            ))
        return order