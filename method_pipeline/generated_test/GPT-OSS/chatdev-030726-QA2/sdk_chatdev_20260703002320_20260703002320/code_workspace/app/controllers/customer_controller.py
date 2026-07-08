"""
Customer API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from app.services.customer_service import CustomerService
from app.controllers.dependencies import get_db

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    service = CustomerService(db)
    return service.create_customer(payload)

@router.get("/{customer_id}", response_model=CustomerOut)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    customer = service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    service = CustomerService(db)
    customer = service.update_customer(customer_id, payload)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    service.delete_customer(customer_id)
    return None
