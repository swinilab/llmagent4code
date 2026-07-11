"""
Payment REST controller.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DomainError, EntityNotFound
from app.domain.schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentVerification,
)
from app.infrastructure.database import get_db
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def process_payment(
    data: PaymentCreate,
    session: AsyncSession = Depends(get_db),
):
    """Process a payment (checkout journey — hot path).

    Rate limiting is applied by the RateLimiterMiddleware (not by a
    per-endpoint decorator) to avoid double rate-limiting.
    """
    svc = PaymentService(session)
    try:
        return await svc.process_payment(data)
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify", response_model=PaymentResponse)
async def verify_payment(
    data: PaymentVerification,
    session: AsyncSession = Depends(get_db),
):
    """Accountant verifies a payment (back-office)."""
    svc = PaymentService(session)
    try:
        return await svc.verify_payment(data)
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = PaymentService(session)
    try:
        return await svc.get_payment(payment_id)
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/by-order/{order_id}", response_model=list[PaymentResponse])
async def list_payments_by_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = PaymentService(session)
    return await svc.list_payments_by_order(order_id)
