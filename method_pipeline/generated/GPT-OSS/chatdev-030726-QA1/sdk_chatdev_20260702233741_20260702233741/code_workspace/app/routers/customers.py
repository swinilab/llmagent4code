# app/routers/customers.py
"""Customer related endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, services, database

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

@router.post("/", response_model=schemas.CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    svc = services.CustomerService(db)
    return svc.create_customer(payload)

@router.get("/{customer_id}", response_model=schemas.CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(database.get_db)):
    svc = services.CustomerService(db)
    cust = svc.get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust
