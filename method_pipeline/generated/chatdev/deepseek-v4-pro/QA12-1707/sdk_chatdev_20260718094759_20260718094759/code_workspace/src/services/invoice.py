"""Invoice business logic."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.invoice import Invoice, InvoiceStatus
from src.repositories.invoice import InvoiceRepository
from src.schemas.invoice import InvoiceCreate
from src.utils.exceptions import ConflictError, NotFoundError


class InvoiceService:
    """Orchestrates invoice creation and lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = InvoiceRepository(session)

    async def create(self, payload: InvoiceCreate, order_subtotal, order_tax, order_total) -> Invoice:
        """Create an invoice for an accepted order."""
        existing = await self.repo.get_by_order_id(payload.order_id)
        if existing:
            raise ConflictError(f"Invoice already exists for order {payload.order_id}")

        today = date.today()
        due = payload.due_date or (today + timedelta(days=30))
        invoice = Invoice(
            order_id=payload.order_id,
            billing_info=payload.billing_info,
            subtotal=order_subtotal,
            tax=order_tax,
            total=order_total,
            issue_date=today,
            due_date=due,
            status=InvoiceStatus.ISSUED,
        )
        return await self.repo.add(invoice)

    async def get(self, invoice_id: str) -> Invoice:
        """Retrieve an invoice by ID."""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Invoice]:
        """List all invoices."""
        return await self.repo.list_all(limit=limit, offset=offset)

    async def get_by_order(self, order_id: str) -> Invoice | None:
        """Fetch invoice by order ID."""
        return await self.repo.get_by_order_id(order_id)

    async def mark_paid(self, invoice_id: str) -> Invoice:
        """Mark an invoice as paid."""
        invoice = await self.get(invoice_id)
        invoice.status = InvoiceStatus.PAID
        await self.repo.session.flush()
        return invoice
