"""
REST controller for Payment entity.
Provides CRUD + verification endpoints under /api/v1/payments.
All workflow steps delegate to OrderWorkflow for orchestration consistency.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate
from app.services.payment_service import PaymentService
from app.workflows.order_workflow import OrderWorkflow

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(data: PaymentCreate, db: AsyncSession = Depends(get_db)):
    """Record a payment (Customer step 4). Delegates to OrderWorkflow."""
    try:
        payment = await OrderWorkflow.pay_invoice(
            db,
            order_id=data.order_id,
            amount=data.amount,
            method=data.method,
            transaction_ref=data.transaction_ref,
            currency=data.currency,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return payment


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a payment by ID."""
    payment = await PaymentService.get_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/", response_model=List[PaymentRead])
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List payments with pagination."""
    payments = await PaymentService.get_all(db, skip=skip, limit=limit)
    return payments


@router.get("/by-order/{order_id}", response_model=List[PaymentRead])
async def get_payments_by_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get all payments for a specific order."""
    payments = await PaymentService.get_by_order(db, order_id)
    return payments


@router.post("/{payment_id}/verify", response_model=PaymentRead)
async def verify_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    """Accountant verifies a payment (step 5).
    Uses OrderWorkflow to verify, update order status to PAID, and mark invoice as paid.
    """
    try:
        payment = await OrderWorkflow.verify_payment(db, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(payment_id: str, data: PaymentUpdate, db: AsyncSession = Depends(get_db)):
    """Update payment fields."""
    payment = await PaymentService.update(db, payment_id, data)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a payment by ID."""
    deleted = await PaymentService.delete(db, payment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Payment not found")
