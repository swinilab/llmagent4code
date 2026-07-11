"""
Routers for Payment endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentVerification
from app.services.payment_service import PaymentService, PaymentStateError

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    return PaymentService.create(db, data)


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    order_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if order_id:
        return PaymentService.list_by_order(db, order_id)
    return PaymentService.list_all(db, skip=skip, limit=limit)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = PaymentService.get_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/pay", response_model=PaymentResponse)
def pay_payment(payment_id: str, db: Session = Depends(get_db)):
    try:
        payment = PaymentService.mark_paid(db, payment_id)
    except PaymentStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    try:
        payment = PaymentService.verify(db, payment_id)
    except PaymentStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/{payment_id}", status_code=204)
def delete_payment(payment_id: str, db: Session = Depends(get_db)):
    if not PaymentService.delete(db, payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
