"""
Payment REST API controller.
Handles HTTP requests for payment operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms.config.database import get_db
from oms.models.payment import PaymentCreate, PaymentProcessRequest, PaymentVerifyRequest, PaymentResponse, PaymentStatus
from oms.services.payment_service import PaymentService

payment_router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@payment_router.get("", response_model=List[PaymentResponse])
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: PaymentStatus = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments with optional filters."""
    service = PaymentService(db)
    if status:
        return await service.get_payments_by_status(status, skip=skip, limit=limit)
    return await service.get_all_payments(skip=skip, limit=limit)


@payment_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    """Get a payment by ID."""
    service = PaymentService(db)
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@payment_router.get("/order/{order_id}", response_model=PaymentResponse)
async def get_payment_by_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get a payment by order ID."""
    service = PaymentService(db)
    payment = await service.get_payment_by_order_id(order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@payment_router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(payment_data: PaymentCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a payment for an order (Customer workflow step 4).
    """
    service = PaymentService(db)
    try:
        return await service.create_payment(payment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.post("/{payment_id}/process", response_model=PaymentResponse)
async def process_payment(
    payment_id: int,
    process_data: PaymentProcessRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a payment (simulate payment gateway).
    """
    service = PaymentService(db)
    transaction_id = process_data.transaction_id if process_data else None
    try:
        payment = await service.process_payment(payment_id, transaction_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.post("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(
    payment_id: int,
    verify_data: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a payment (Accountant workflow step 5).
    """
    service = PaymentService(db)
    payment = await service.verify_payment(
        payment_id,
        confirmed=verify_data.confirmed,
        notes=verify_data.notes
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@payment_router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Refund a payment."""
    service = PaymentService(db)
    try:
        payment = await service.refund_payment(payment_id, notes=notes)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(payment_id: int, payment_data: PaymentCreate, db: AsyncSession = Depends(get_db)):
    """Update a payment."""
    service = PaymentService(db)
    update_data = payment_data.model_dump(exclude_unset=True)
    payment = await service.update_payment(payment_id, **update_data)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@payment_router.delete("/{payment_id}", status_code=204)
async def delete_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a payment."""
    service = PaymentService(db)
    deleted = await service.delete_payment(payment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Payment not found")
    return None


@payment_router.get("/count")
async def get_payment_count(db: AsyncSession = Depends(get_db)):
    """Get total number of payments."""
    service = PaymentService(db)
    return {"count": await service.get_payment_count()}
