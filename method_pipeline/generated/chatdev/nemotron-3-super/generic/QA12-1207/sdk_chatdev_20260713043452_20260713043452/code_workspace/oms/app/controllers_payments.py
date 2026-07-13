from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=List[schemas.Payment])
async def read_payments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve payments.
    """
    payments = await crud.get_payments(db, skip=skip, limit=limit)
    return payments


@router.get("/{payment_id}", response_model=schemas.Payment)
async def read_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific payment by ID.
    """
    payment = await crud.get_payment(db, payment_id=payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.put("/{payment_id}", response_model=schemas.Payment)
async def update_payment(
    payment_id: int,
    payment_in: schemas.PaymentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a payment.
    """
    payment = await crud.update_payment(
        db, payment_id=payment_id, payment_in=payment_in
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/{payment_id}", response_model=schemas.Payment)
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a payment.
    """
    payment = await crud.delete_payment(db, payment_id=payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment