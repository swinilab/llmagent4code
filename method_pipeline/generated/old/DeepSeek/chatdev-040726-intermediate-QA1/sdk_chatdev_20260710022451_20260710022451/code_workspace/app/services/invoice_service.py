"""
Invoice service — handles invoice creation and lifecycle.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.domain.enums import InvoiceStatus, OrderStatus
from app.domain.exceptions import (
    EntityNotFound,
    InvalidOrderStateTransition,
    InvoiceAlreadyIssued,
    OptimisticLockError,
)
from app.domain.models import Invoice, Order
from app.domain.schemas import InvoiceCreate
from app.infrastructure.queue import publish_message
from app.repositories.invoice import InvoiceRepository
from app.repositories.order import OrderRepository


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invoice_repo = InvoiceRepository(session)
        self._order_repo = OrderRepository(session)

    async def get_invoice(self, invoice_id: int) -> Invoice:
        """Retrieve an invoice by ID."""
        return await self._invoice_repo.get_or_fail(invoice_id)

    async def create_invoice(self, data: InvoiceCreate) -> Invoice:
        """Accountant creates an invoice for an accepted order (back-office)."""
        order = await self._order_repo.get_with_items_or_fail(data.order_id)

        # Optimistic lock check
        if order.version != data.version:
            raise OptimisticLockError()

        # Order must be ACCEPTED
        if order.status != OrderStatus.ACCEPTED:
            raise InvalidOrderStateTransition(
                order.status.value, "INVOICED"
            )

        # Check no invoice already exists
        existing = await self._session.execute(
            select(Invoice).where(
                Invoice.order_id == data.order_id,
                Invoice.status != InvoiceStatus.CANCELLED,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise InvoiceAlreadyIssued()

        issue_date = date.today()
        due_date = data.due_date or (issue_date + timedelta(days=30))

        invoice = Invoice(
            order_id=data.order_id,
            billing_name=data.billing_name,
            billing_address=data.billing_address,
            total_amount=order.total_amount,
            currency=order.currency,
            status=InvoiceStatus.ISSUED,
            issue_date=issue_date,
            due_date=due_date,
        )
        created = await self._invoice_repo.add(invoice)

        # Transition order to INVOICED
        order.status = OrderStatus.INVOICED
        order.updated_at = datetime.now(timezone.utc)
        self._session.add(order)

        try:
            await self._session.flush()
        except StaleDataError:
            raise OptimisticLockError()
        await publish_message(
            "oms.notifications",
            {
                "type": "invoice.created",
                "invoice_id": created.id,
                "order_id": data.order_id,
            },
        )

        return created

    async def list_invoices_by_order(self, order_id: int) -> list[Invoice]:
        result = await self._session.execute(
            select(Invoice).where(Invoice.order_id == order_id).order_by(Invoice.created_at)
        )
        return list(result.scalars().all())
