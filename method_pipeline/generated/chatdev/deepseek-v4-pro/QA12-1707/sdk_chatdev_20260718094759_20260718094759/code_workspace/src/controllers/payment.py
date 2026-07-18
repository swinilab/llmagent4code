"""
Payment REST controller.

Endpoints:
  POST   /api/v1/payments              — create payment
  GET    /api/v1/payments              — list payments
  GET    /api/v1/payments/{id}         — get payment
  GET    /api/v1/payments/order/{id}   — payments by order
  PATCH  /api/v1/payments/{id}/verify  — verify payment
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.payment import PaymentCreate, PaymentResponse, PaymentVerify
from src.services.payment import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(payload: PaymentCreate, session: AsyncSession = Depends(get_session)):
    """Record a new payment."""
    svc = PaymentService(session)
    return await svc.create(payload)


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all payments."""
    svc = PaymentService(session)
    return await svc.list_all(limit=limit, offset=offset)


@router.get("/order/{order_id}", response_model=list[PaymentResponse])
async def payments_by_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List payments for an order."""
    svc = PaymentService(session)
    return await svc.list_by_order(order_id)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve a payment by ID."""
    svc = PaymentService(session)
    return await svc.get(payment_id)


@router.patch("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(
    payment_id: str,
    payload: PaymentVerify,
    session: AsyncSession = Depends(get_session),
):
    """Verify a payment (complete or fail)."""
    svc = PaymentService(session)
    return await svc.verify(payment_id, payload.status)
