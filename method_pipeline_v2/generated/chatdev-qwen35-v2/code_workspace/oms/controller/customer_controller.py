"""
Customer controller with REST endpoints
Implements NFR 2.1 Exception Detection via validation and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from oms.infrastructure.database import get_async_session
from oms.service.customer_service import CustomerService
from oms.domain.models import Customer, CustomerCreate
from oms.infrastructure.exceptions import (
    ValidationException, NotFoundException,
    oms_exception_handler, validation_exception_handler
)
from oms.infrastructure.event.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

def get_customer_service(session: AsyncSession = Depends(get_async_session)) -> CustomerService:
    """Get customer service instance"""
    return CustomerService(session)

@router.get("", response_model=List[Customer])
async def list_customers(
    service: CustomerService = Depends(get_customer_service)
):
    """List all customers"""
    return await service.get_all()

@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service)
):
    """Get customer by ID"""
    try:
        return await service.get_by_id(customer_id)
    except NotFoundException as e:
        raise e

@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    service: CustomerService = Depends(get_customer_service)
):
    """
    Create new customer
    NFR 1.1: Rate limited
    """
    # Check rate limit (NFR 1.1)
    rate_limiter = RateLimiter.get_instance()
    if not await rate_limiter.is_allowed("customer_create"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return await service.create(customer)

@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: str,
    customer: CustomerCreate,
    service: CustomerService = Depends(get_customer_service)
):
    """Update existing customer"""
    return await service.update(customer_id, customer)

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service)
):
    """Delete customer"""
    success = await service.delete(customer_id)
    if not success:
        raise NotFoundException(f"Customer {customer_id} not found")

customer_router = router
