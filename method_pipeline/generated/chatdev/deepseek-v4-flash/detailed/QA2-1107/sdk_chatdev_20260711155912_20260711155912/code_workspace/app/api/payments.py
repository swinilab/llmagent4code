"""
Payment API endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.models import Payment
from app.domain.schemas import PaymentCreate, PaymentResponse
from app.infrastructure.database import get_db_session
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def process_payment(
    data: PaymentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Payment:
    """Step 4: Customer pays invoice."""
    service = PaymentService(session)
    return await service.process_payment(data)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Payment:
    service = PaymentService(session)
    payment = await service.get_payment(payment_id)
    if payment is None:
        raise NotFoundError(f"Payment {payment_id} not found")
    return payment


@router.get("/by-order/{order_id}", response_model=list[PaymentResponse])
async def get_payments_by_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[Payment]:
    service = PaymentService(session)
    return await service.get_payments_by_order(order_id)


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Payment:
    """Step 5: Accountant verifies payment."""
    service = PaymentService(session)
    return await service.verify_payment(payment_id)
