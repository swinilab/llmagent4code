"""
Invoice controller — REST endpoint handlers for invoice operations.

Covers invoice creation (step 3), listing, and status updates.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from oms.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceStatusUpdate
from oms.schemas.common import PaginatedResponse
from oms.services.invoice import InvoiceService, InvoiceError


class InvoiceController:
    """Handles invoice CRUD and status endpoints."""

    async def create_invoice(self, data: InvoiceCreate, session: AsyncSession) -> InvoiceRead:
        service = InvoiceService(session)
        try:
            invoice = await service.create_invoice(data)
        except InvoiceError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return InvoiceRead.model_validate(invoice)

    async def get_invoice(self, invoice_id: str, session: AsyncSession) -> InvoiceRead:
        service = InvoiceService(session)
        invoice = await service.get_invoice(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        return InvoiceRead.model_validate(invoice)

    async def get_invoice_by_order(self, order_id: str, session: AsyncSession) -> InvoiceRead:
        service = InvoiceService(session)
        invoice = await service.get_invoice_by_order(order_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"No invoice for order {order_id}")
        return InvoiceRead.model_validate(invoice)

    async def list_invoices(self, session: AsyncSession, page: int = 1, page_size: int = 20) -> PaginatedResponse[InvoiceRead]:
        service = InvoiceService(session)
        items, total = await service.list_invoices(page=page, page_size=page_size)
        return PaginatedResponse[InvoiceRead].create(
            items=[InvoiceRead.model_validate(i) for i in items],
            total=total, page=page, page_size=page_size,
        )

    async def update_invoice_status(self, invoice_id: str, data: InvoiceStatusUpdate, session: AsyncSession) -> InvoiceRead:
        service = InvoiceService(session)
        invoice = await service.update_invoice_status(invoice_id, data)
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        return InvoiceRead.model_validate(invoice)

    async def mark_overdue(self, session: AsyncSession) -> dict:
        """Mark all overdue invoices (admin/cron endpoint)."""
        service = InvoiceService(session)
        updated = await service.mark_overdue_invoices()
        return {"marked_overdue": len(updated)}


invoice_controller = InvoiceController()