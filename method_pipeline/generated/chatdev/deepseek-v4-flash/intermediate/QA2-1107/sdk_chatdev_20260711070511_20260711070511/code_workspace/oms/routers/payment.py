"""
Payment REST router.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.schemas.payment import PaymentCreate, PaymentResponse
from oms.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    service = PaymentService(db)
    try:
        payment = service.create_payment(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    service = PaymentService(db)
    payment = service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    service = PaymentService(db)
    try:
        payment = service.verify_payment(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(payment)
    return payment


@router.get("/by-order/{order_id}", response_model=List[PaymentResponse])
def list_payments_by_order(order_id: str, db: Session = Depends(get_db)):
    service = PaymentService(db)
    return service.list_by_order(order_id)
