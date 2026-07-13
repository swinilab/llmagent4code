from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.app.db.session import get_db
from oms_backend.app.services import payment_service
from oms_backend.app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse

router = APIRouter()

@router.get("/", response_model=list[PaymentResponse])
def read_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    payments = payment_service.get_payments(db, skip=skip, limit=limit)
    return payments

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payment_in: PaymentCreate, db: Session = Depends(get_db)):
    return payment_service.create_payment(db, payment_in)

@router.get("/{payment_id}", response_model=PaymentResponse)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    db_obj = payment_service.get_payment(db, payment_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_obj

@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(payment_id: int, payment_in: PaymentUpdate, db: Session = Depends(get_db)):
    db_obj = payment_service.get_payment(db, payment_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    updated = payment_service.update_payment(db, payment_id, payment_in)
    return updated

@router.delete("/{payment_id}", response_model=PaymentResponse)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    db_obj = payment_service.get_payment(db, payment_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    deleted = payment_service.delete_payment(db, db_obj.id)
    return deleted