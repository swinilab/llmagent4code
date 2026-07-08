"""
Customer REST endpoints (v1).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oms.domain.models import Customer, CreateCustomerRequest
from oms.service.customer_service import CustomerService
from oms.api.deps import get_customer_service

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
def register_customer(
    request: CreateCustomerRequest,
    service: CustomerService = Depends(get_customer_service),
) -> Customer:
    """Register a new customer."""
    return service.register(request)


@router.get("", response_model=list[Customer])
def list_customers(
    service: CustomerService = Depends(get_customer_service),
) -> list[Customer]:
    """List all registered customers."""
    return service.list_all()


@router.get("/{customer_id}", response_model=Customer)
def get_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
) -> Customer:
    """Get a customer by ID."""
    customer = service.get_by_id(customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer
