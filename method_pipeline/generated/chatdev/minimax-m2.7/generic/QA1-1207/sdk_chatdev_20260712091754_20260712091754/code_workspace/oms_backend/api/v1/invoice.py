"""
InvoiceController — REST endpoints for invoice lifecycle.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.db.connection import get_session
from oms_backend.schemas.domain import Invoice, InvoiceCreate, InvoiceIssue, InvoicePay, paginate
from oms_backend.services.invoice import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _parse_actor(x_actor_id: str | None) -> uuid.UUID | None:
    """Parse X-Actor-ID header into a UUID, or return None."""
    if not x_actor_id:
        return None
    try:
        return uuid.UUID(x_actor_id)
    except ValueError:
        return None


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """
    Accountant creates a draft invoice for an accepted order.
    Workflow step 3.
    """
    svc = InvoiceService(session)
    try:
        return await svc.create_from_order(data.order_id, data, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get an invoice by ID."""
    svc = InvoiceService(session)
    invoice = await svc.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/order/{order_id}", response_model=Invoice)
async def get_invoice_by_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get the invoice attached to a specific order."""
    svc = InvoiceService(session)
    invoice = await svc.get_by_order(order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for this order")
    return invoice


@router.get("", response_model=dict)
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_session)],
    customer_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all invoices (optionally filtered by customer)."""
    svc = InvoiceService(session)
    if customer_id:
        invoices, total = await svc.list_by_customer(customer_id, page=page, page_size=page_size)
    else:
        invoices, total = await svc.list_all(page=page, page_size=page_size)
    return paginate(
        [Invoice.model_validate(inv) for inv in invoices],
        total=total, page=page, page_size=page_size
    ).model_dump()


# ── Lifecycle: Issue ───────────────────────────────────────────────────────────

@router.post("/{invoice_id}/issue", response_model=Invoice)
async def issue_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceIssue,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """
    Accountant issues a draft invoice (makes it enforceable).
    """
    svc = InvoiceService(session)
    try:
        invoice = await svc.issue(invoice_id, data, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Mark Paid ───────────────────────────────────────────────────────

@router.post("/{invoice_id}/pay", response_model=Invoice)
async def pay_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    data: InvoicePay | None = None,
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """
    Accountant records that an invoice has been paid (without going through the payment gateway).
    Workflow step 5 (accountant verifies payment).
    """
    svc = InvoiceService(session)
    try:
        invoice = await svc.mark_paid(invoice_id, data, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Cancel ─────────────────────────────────────────────────────────---

@router.post("/{invoice_id}/cancel", response_model=Invoice)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """
    Accountant cancels a draft or issued invoice.
    """
    svc = InvoiceService(session)
    try:
        invoice = await svc.cancel(invoice_id, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Void ─────────────────────────────────────────────────────────---

@router.post("/{invoice_id}/void", response_model=Invoice)
async def void_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """
    Accountant voids a paid invoice (issues credit note internally).
    """
    svc = InvoiceService(session)
    try:
        invoice = await svc.void(invoice_id, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
