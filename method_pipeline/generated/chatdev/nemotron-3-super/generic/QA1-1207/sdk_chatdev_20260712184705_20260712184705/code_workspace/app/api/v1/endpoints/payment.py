from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import payment_service
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse

router = APIRouter()

@router.get("/", response_model=List[PaymentResponse])
async def read_payments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.get_payments(db, skip=skip, limit=limit)

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.create_payment(db, payment_in)

@router.get("/{payment_id}", response_model=PaymentResponse)
async def read_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
):
    payment = await payment_service.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_in: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
):
    payment = await payment_service.update_payment(db, payment_id, payment_in)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await payment_service.delete_payment(db, payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")
    return None

@router.get("/order/{order_id}", response_model=Optional[PaymentResponse])
async def get_payment_by_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    payment = await payment_service.get_payment_by_order(db, order_id)
    return payment