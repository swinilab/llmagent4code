"""FastAPI controller for Customer endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.customer_service import CustomerService
from ..database import get_session
from ..models import Customer
from pydantic import BaseModel

router = APIRouter(prefix="/customers", tags=["customers"])

class CustomerCreate(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: str

@router.post("/", response_model=Customer, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, session: Session = Depends(get_session)):
    try:
        return CustomerService.create_customer(
            session,
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            banking_details=payload.banking_details,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{customer_id}", response_model=Customer)
def get_customer(customer_id: int, session: Session = Depends(get_session)):
    customer = CustomerService.get_customer(session, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.get("/", response_model=list[Customer])
def list_customers(session: Session = Depends(get_session)):
    return CustomerService.list_customers(session)