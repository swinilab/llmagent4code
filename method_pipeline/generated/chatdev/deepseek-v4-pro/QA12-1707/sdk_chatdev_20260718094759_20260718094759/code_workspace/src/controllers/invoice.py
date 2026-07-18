"""
Invoice REST controller.

Endpoints:
  POST   /api/v1/invoices              — create invoice
  GET    /api/v1/invoices              — list invoices
  GET    /api/v1/invoices/{id}         — get invoice
  GET    /api/v1/invoices/order/{id}   — invoice by order
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.invoice import InvoiceCreate, InvoiceResponse
from src.services.invoice import InvoiceService
from src.services.order import OrderService
from src.utils.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(payload: InvoiceCreate, session: AsyncSession = Depends(get_session)):
    """Create an invoice for an accepted order."""
    order_svc = OrderService(session)
    order = await order_svc.get(payload.order_id)
    invoice_svc = InvoiceService(session)
    invoice = await invoice_svc.create(payload, order.subtotal, order.tax, order.total)
    return invoice


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all invoices."""
    svc = InvoiceService(session)
    return await svc.list_all(limit=limit, offset=offset)


@router.get("/order/{order_id}", response_model=InvoiceResponse)
async def invoice_by_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve invoice by order ID."""
    svc = InvoiceService(session)
    invoice = await svc.get_by_order(order_id)
    if not invoice:
        raise NotFoundError(f"No invoice found for order {order_id}")
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve an invoice by ID."""
    svc = InvoiceService(session)
    return await svc.get(invoice_id)
