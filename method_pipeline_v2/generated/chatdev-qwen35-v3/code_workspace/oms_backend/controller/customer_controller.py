"""
Customer REST API controller
Implements validation and request/response mapping
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms_backend.repository.base import get_db
from oms_backend.service.customer_service import CustomerService
from oms_backend.domain.schemas import CustomerCreate, CustomerResponse
from oms_backend.domain.models import Customer

customer_router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def customer_to_response(customer: Customer) -> CustomerResponse:
    """Convert Customer model to response schema"""
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        bankingDetails=customer.banking_details,
        role=customer.role,
        orderHistory=customer.order_history or [],
        createdAt=customer.created_at,
        updatedAt=customer.updated_at
    )


@customer_router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db)
) -> CustomerResponse:
    """Create a new customer"""
    service = CustomerService(session)
    try:
        customer = await service.create_customer(data)
        return customer_to_response(customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@customer_router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db)
) -> CustomerResponse:
    """Get customer by ID"""
    import uuid
    try:
        uuid.UUID(customer_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = CustomerService(session)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer_to_response(customer)


@customer_router.get("", response_model=List[CustomerResponse])
async def get_all_customers(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> List[CustomerResponse]:
    """Get all customers with pagination"""
    service = CustomerService(session)
    customers = await service.get_all_customers(limit, offset)
    return [customer_to_response(c) for c in customers]
