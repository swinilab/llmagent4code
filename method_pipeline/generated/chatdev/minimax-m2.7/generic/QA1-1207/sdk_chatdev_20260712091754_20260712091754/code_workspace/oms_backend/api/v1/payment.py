"""
PaymentController — REST endpoints for payment processing.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.db.connection import get_session
from oms_backend.schemas.domain import Payment, PaymentCreate, PaymentWebhookPayload, paginate
from oms_backend.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Create / Process ────────────────────────────────────────────────────────────

@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Process payment for an invoice (authorize + capture).
    Workflow step 4 (customer pays invoice).
    Uses circuit breaker on payment gateway (NFR 1.3).
    """
    svc = PaymentService(session)
    try:
        return await svc.authorize_and_capture(data, ip_address=_client_ip(request))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Webhook ────────────────────────────────────────────────────────────────────

@router.post("/webhook", response_model=Payment | None)
async def payment_webhook(
    payload: PaymentWebhookPayload,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Receive payment gateway webhook to update payment status.
    Processes: authorized, captured, failed, refunded.
    """
    svc = PaymentService(session)
    payment = await svc.handle_webhook(payload, ip_address=_client_ip(request))
    return payment


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a payment by ID."""
    svc = PaymentService(session)
    payment = await svc.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/invoice/{invoice_id}", response_model=dict)
async def list_payments_by_invoice(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """List all payments for an invoice."""
    svc = PaymentService(session)
    payments = await svc.list_by_invoice(invoice_id)
    return paginate(
        [Payment.model_validate(p) for p in payments],
        total=len(payments), page=1, page_size=len(payments)
    ).model_dump()


@router.get("", response_model=dict)
async def list_payments(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all payments (paginated)."""
    svc = PaymentService(session)
    payments, total = await svc.list_all(page=page, page_size=page_size)
    return paginate(
        [Payment.model_validate(p) for p in payments],
        total=total, page=page, page_size=page_size
    ).model_dump()


# ── Refund ─────────────────────────────────────────────────────────────────────

@router.post("/{payment_id}/refund", response_model=Payment)
async def refund_payment(
    payment_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Refund a captured payment (accountant action)."""
    svc = PaymentService(session)
    try:
        payment = await svc.refund(payment_id, ip_address=_client_ip(request))
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
