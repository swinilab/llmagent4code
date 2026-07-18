"""
Customer REST controller.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.customer import CustomerService
from app.schemas.customer import CustomerCreate, CustomerRead
from app.db.session import get_db

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer."""
    service = CustomerService(db)
    return service.create_customer(customer)


@router.get("/{customer_id}", response_model=CustomerRead)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer by ID."""
    service = CustomerService(db)
    return service.get_customer(customer_id)


@router.get("", response_model=list[CustomerRead])
def read_customers(db: Session = Depends(get_db)):
    """List all customers."""
    service = CustomerService(db)
    return service.list_customers()