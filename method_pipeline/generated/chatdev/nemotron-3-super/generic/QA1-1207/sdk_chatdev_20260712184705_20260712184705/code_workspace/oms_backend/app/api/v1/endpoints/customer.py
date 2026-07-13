from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.app.db.session import get_db
from oms_backend.app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from oms_backend.app.services import customer_service

router = APIRouter()

@router.get("/", response_model=list[CustomerResponse])
def read_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    customers = customer_service.get_customers(db, skip=skip, limit=limit)
    return customers

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db)):
    return customer_service.create_customer(db, customer_in)

@router.get("/{customer_id}", response_model=CustomerResponse)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    db_obj = customer_service.get_customer(db, customer_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db_obj

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, customer_in: CustomerUpdate, db: Session = Depends(get_db)):
    db_obj = customer_service.get_customer(db, customer_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    updated = customer_service.update_customer(db, customer_id, customer_in)
    return updated

@router.delete("/{customer_id}", response_model=CustomerResponse)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    db_obj = customer_service.get_customer(db, customer_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    deleted = customer_service.delete_customer(db, db_obj.id)
    return deleted