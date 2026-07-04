"""Payment REST controller — v1 API.

Uses WorkflowService to orchestrate the full lifecycle transitions.
WorkflowError propagates to the global handler in main.py for ACID compliance.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.models import Payment, PaymentMethod
from app.services.payment_service import PaymentService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/payments", tags=["Payments"])


class CreatePaymentRequest(BaseModel):
    order_id: str
    invoice_id: str
    amount: Decimal
    method: PaymentMethod


class StatusUpdateResponse(BaseModel):
    payment: Payment
    message: str


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(body: CreatePaymentRequest, db: AsyncSession = Depends(get_db)):
    svc = PaymentService(db)
    return await svc.create_payment(
        order_id=body.order_id,
        invoice_id=body.invoice_id,
        amount=body.amount,
        method=body.method,
    )


@router.get("", response_model=list[Payment])
async def list_payments(db: AsyncSession = Depends(get_db)):
    svc = PaymentService(db)
    return await svc.list_payments()


@router.get("/{payment_id}", response_model=Payment)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    svc = PaymentService(db)
    payment = await svc.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/complete", response_model=StatusUpdateResponse)
async def complete_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    """Accountant verifies and completes a payment (Step 5).

    WorkflowError propagates to the global exception handler, which
    returns a 409 response only AFTER the DB transaction is rolled back
    by get_db(), preserving ACID guarantees.
    """
    workflow = WorkflowService(db)
    payment = await workflow.verify_payment(payment_id)
    return StatusUpdateResponse(payment=payment, message="Payment completed and order verified")