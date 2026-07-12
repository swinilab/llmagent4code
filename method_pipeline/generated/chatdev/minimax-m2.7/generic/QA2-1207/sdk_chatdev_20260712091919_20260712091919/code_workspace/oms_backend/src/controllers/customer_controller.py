"""
Customer Controller - REST endpoints for customer management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.customer_service import CustomerService
from ..domain.models import Address, BankingDetails, UserRole

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


class AddressModel(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class BankingDetailsModel(BaseModel):
    bank_name: str
    account_number: str
    routing_number: str
    account_type: str = "checking"


class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = ""
    address: Optional[AddressModel] = None
    banking_details: Optional[BankingDetailsModel] = None
    role: str = "customer"


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[AddressModel] = None
    banking_details: Optional[BankingDetailsModel] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    address: Optional[AddressModel] = None
    banking_details: Optional[dict] = None
    role: str
    created_at: str
    updated_at: str


def _to_response(customer) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=AddressModel(**customer.address.to_dict()) if customer.address else None,
        banking_details=customer.banking_details.to_dict() if customer.banking_details else None,
        role=customer.role.value if hasattr(customer.role, 'value') else customer.role,
        created_at=customer.created_at.isoformat(),
        updated_at=customer.updated_at.isoformat()
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    request: CreateCustomerRequest,
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    service = CustomerService(db)
    
    address = None
    if request.address:
        address = Address.from_dict(request.address.dict())
    
    banking = None
    if request.banking_details:
        banking = BankingDetails(
            bank_name=request.banking_details.bank_name,
            account_number=request.banking_details.account_number,
            routing_number=request.banking_details.routing_number,
            account_type=request.banking_details.account_type
        )
    
    role = UserRole.CUSTOMER
    if request.role in ["customer", "order_staff", "accountant"]:
        role = UserRole(request.role)
    
    customer = service.create_customer(
        name=request.name,
        email=request.email,
        phone=request.phone or "",
        address=address,
        banking_details=banking,
        role=role
    )
    return _to_response(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get customer by ID."""
    service = CustomerService(db)
    customer = service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _to_response(customer)


@router.get("/by-email/{email}", response_model=CustomerResponse)
def get_customer_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """Get customer by email."""
    service = CustomerService(db)
    customer = service.get_customer_by_email(email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _to_response(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: str,
    request: UpdateCustomerRequest,
    db: Session = Depends(get_db)
):
    """Update customer fields."""
    service = CustomerService(db)
    
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.email is not None:
        update_data["email"] = request.email
    if request.phone is not None:
        update_data["phone"] = request.phone
    
    customer = service.update_customer(customer_id, **update_data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _to_response(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Delete a customer."""
    service = CustomerService(db)
    success = service.delete_customer(customer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all customers."""
    service = CustomerService(db)
    customers = service.list_customers(skip=skip, limit=limit)
    return [_to_response(c) for c in customers]
