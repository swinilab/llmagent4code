"""FastAPI router for customer endpoints.
All routes are versioned under /api/{API_VERSION}/customers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import CustomerCreate, CustomerRead
from services import CustomerService
from database import get_db
from config import get_settings

settings = get_settings()
router = APIRouter(prefix=f"/api/{settings.API_VERSION}/customers", tags=["customers"])

@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    service = CustomerService(db)
    try:
        cust = service.create_customer(payload.dict())
        return cust
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    cust = service.get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust