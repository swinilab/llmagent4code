"""
Invoice REST controller.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DomainError
from app.domain.schemas import InvoiceCreate, InvoiceResponse
from app.infrastructure.database import get_db
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    session: AsyncSession = Depends(get_db),
):
    """Accountant creates an invoice (back-office)."""
    svc = InvoiceService(session)
    try:
        return await svc.create_invoice(data)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = InvoiceService(session)
    try:
        return await svc.get_invoice(invoice_id)
    except DomainError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/by-order/{order_id}", response_model=list[InvoiceResponse])
async def list_invoices_by_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = InvoiceService(session)
    return await svc.list_invoices_by_order(order_id)
