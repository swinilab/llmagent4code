"""
Invoice service: handles invoice creation and management.

Criticality: CORE (NFR 2.1) — invoicing is part of the order-to-cash flow.
Recovery: Retry on transient DB errors (NFR 2.2); manual intervention
required for invoice generation failures.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbox import OutboxRepository
from app.adapters.repositories import InvoiceRepository, OrderRepository
from app.domain.enums import InvoiceStatus, OrderStatus
from app.domain.models import Invoice
from app.domain.schemas import InvoiceCreate
from app.domain.state_machine import TransitionEvent
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class InvoiceService:
    """Encapsulates invoice business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invoice_repo = InvoiceRepository(session)
        self._order_repo = OrderRepository(session)
        self._outbox_repo = OutboxRepository(session)

    async def create_invoice(self, data: InvoiceCreate) -> Invoice:
        """
        Create an invoice for an accepted order (workflow step 3).

        Delegates the order state transition (ACCEPTED -> INVOICED) to
        OrderService.transition_order(), which enforces the domain state
        machine via apply_transition() — ensuring the state machine
        remains the single source of truth for all transitions (see ADR-003).

        The invoice_ref is passed to transition_order() so it is set
        atomically with the status update in a single SQL UPDATE,
        preventing race conditions (NFR 2.3).
        """
        # Validate order exists and is in ACCEPTED state
        order = await self._order_repo.get(data.order_id)
        if order is None:
            raise ValueError(f"Order {data.order_id} not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(
                f"Order {data.order_id} is in status '{order.status.value}', "
                f"expected 'ACCEPTED'. Cannot create invoice."
            )

        # Validate invoice amount matches order total
        # If amount is not provided (None sentinel), default to order total
        invoice_amount = data.amount if data.amount is not None else order.total_amount
        if abs(invoice_amount - order.total_amount) > 0.01:
            raise ValueError(
                f"Invoice amount {invoice_amount} does not match order total "
                f"{order.total_amount} for order {data.order_id}. "
                f"Difference exceeds tolerance of 0.01."
            )

        # Create the invoice
        invoice = Invoice(
            order_id=data.order_id,
            billing_info=data.billing_info,
            amount=invoice_amount,
            currency=data.currency,
            due_date=data.due_date,
            status=InvoiceStatus.ISSUED,
        )
        invoice = await self._invoice_repo.create(invoice)

        # Delegate the state transition to OrderService, which calls
        # apply_transition() and persists the new status + invoice_ref
        # atomically via the repository's update_status().
        order_service = OrderService(self._session)
        try:
            await order_service.transition_order(
                order_id=data.order_id,
                event=TransitionEvent.CREATE_INVOICE,
                invoice_ref=str(invoice.id),
            )
        except ValueError as exc:
            # If the transition fails (e.g., optimistic lock conflict),
            # the invoice was already created — manual intervention needed.
            logger.error(
                "Invoice %s created but order %s transition failed: %s",
                invoice.id,
                data.order_id,
                exc,
            )
            raise

        logger.info(
            "Invoice %s created for order %s (amount=%.2f, invoice_ref set)",
            invoice.id,
            data.order_id,
            invoice_amount,
        )
        return invoice

    async def get_invoice(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self._invoice_repo.get(invoice_id)

    async def get_invoices_by_order(self, order_id: uuid.UUID) -> list[Invoice]:
        return list(await self._invoice_repo.get_by_order(order_id))
