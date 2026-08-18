"""
Customer controller
REST endpoints for customer operations
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.infrastructure.database import get_db
from oms_backend.service import CustomerService
from oms_backend.domain.models import Customer, CustomerCreate
from oms_backend.controller.responses import ErrorResponse
from oms_backend.utils.exceptions import OMSException, NotFoundException, ValidationException
from oms_backend.utils.rate_limiter import rate_limiter


router = APIRouter(prefix="/customers", tags=["customers"])


@router.post(
    "",
    response_model=Customer,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create a new customer",
    description="Create a new customer with the provided details.",
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new customer.
    NFR 1.1: Rate limiting applied.
    """
    # Rate limiting check (NFR 1.1)
    if not rate_limiter.is_allowed("create_customer"):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": 60}
        )
    
    service = CustomerService(db)
    try:
        return service.create_customer(data)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "",
    response_model=List[Customer],
    summary="Get all customers",
    description="Retrieve a list of all customers.",
)
def get_all_customers(db: Session = Depends(get_db)):
    """Get all customers."""
    service = CustomerService(db)
    return service.get_all_customers()


@router.get(
    "/{customer_id}",
    response_model=Customer,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
    },
    summary="Get customer by ID",
    description="Retrieve a customer by their unique ID.",
)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """
    Get customer by ID.
    Validates UUID format and handles not found.
    """
    # Validate UUID format
    try:
        uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid UUID format"}
        )
    
    service = CustomerService(db)
    try:
        return service.get_customer(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.put(
    "/{customer_id}",
    response_model=Customer,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID or validation error"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
    },
    summary="Update customer",
    description="Update an existing customer's details.",
)
def update_customer(
    customer_id: str,
    data: dict,
    db: Session = Depends(get_db),
):
    """Update customer by ID."""
    try:
        uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = CustomerService(db)
    try:
        return service.update_customer(uuid, data)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
    },
    summary="Delete customer",
    description="Delete a customer by their unique ID.",
)
def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    """Delete customer by ID."""
    try:
        uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = CustomerService(db)
    try:
        service.delete_customer(uuid)
        return None
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})
