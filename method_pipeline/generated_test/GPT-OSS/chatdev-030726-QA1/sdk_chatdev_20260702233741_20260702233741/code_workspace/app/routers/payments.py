# app/routers/payments.py
"""Payment endpoints (read‑only for demo)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, services, database

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

def get_payment_service(db: Session = Depends(database.get_db)):
    return services.PaymentService(db)

@router.get("/{payment_id}", response_model=schemas.PaymentRead)
def get_payment(payment_id: int, svc: services.PaymentService = Depends(get_payment_service)):
    pay = svc.get_payment(payment_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")
    return pay
