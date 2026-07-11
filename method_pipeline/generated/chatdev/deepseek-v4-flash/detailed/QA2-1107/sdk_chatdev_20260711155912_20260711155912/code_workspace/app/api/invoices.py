"""
Invoice API endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.models import Invoice
from app.domain.schemas import InvoiceCreate, InvoiceResponse
from app.infrastructure.database import get_db_session
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Invoice:
    """Step 3: Accountant creates invoice for accepted order."""
    service = InvoiceService(session)
    return await service.create_invoice(data)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Invoice:
    service = InvoiceService(session)
    invoice = await service.get_invoice(invoice_id)
    if invoice is None:
        raise NotFoundError(f"Invoice {invoice_id} not found")
    return invoice


@router.get("/by-order/{order_id}", response_model=list[InvoiceResponse])
async def get_invoices_by_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[Invoice]:
    service = InvoiceService(session)
    return await service.get_invoices_by_order(order_id)
