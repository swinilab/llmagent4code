"""
Customer controller with REST endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.connection_pool import get_db
from app.services.customer_service import CustomerService
from app.models.customer import Customer, CustomerRole
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


class CustomerCreateRequest(BaseModel):
    """Request model for creating a customer"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15)
    accountNumber: str = Field(..., min_length=6, max_length=20)
    bankName: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default=CustomerRole.CUSTOMER)


class CustomerResponse(BaseModel):
    """Response model for customer"""
    id: str
    name: str
    address: str
    phone: str
    bankingDetails: dict
    role: str
    orderHistory: List[str]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(request: CustomerCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new customer"""
    service = CustomerService(session)
    try:
        customer = await service.create_customer(
            name=request.name,
            address=request.address,
            phone=request.phone,
            account_number=request.accountNumber,
            bank_name=request.bankName,
            role=request.role,
        )
        return CustomerResponse(
            id=str(customer.id),
            name=customer.name,
            address=customer.address,
            phone=customer.phone,
            bankingDetails=customer.bankingDetails.model_dump(),
            role=customer.role,
            orderHistory=[str(oid) for oid in customer.orderHistory],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.get("", response_model=List[CustomerResponse])
async def list_customers(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    """List all customers"""
    service = CustomerService(session)
    try:
        customers = await service.get_all_customers(limit, offset)
        return [
            CustomerResponse(
                id=str(c.id),
                name=c.name,
                address=c.address,
                phone=c.phone,
                bankingDetails=c.bankingDetails.model_dump(),
                role=c.role,
                orderHistory=[str(oid) for oid in c.orderHistory],
            )
            for c in customers
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, session: AsyncSession = Depends(get_db)):
    """Get customer by ID"""
    service = CustomerService(session)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse(
        id=str(customer.id),
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        bankingDetails=customer.bankingDetails.model_dump(),
        role=customer.role,
        orderHistory=[str(oid) for oid in customer.orderHistory],
    )
