"""
Customer controller for handling customer-related HTTP requests.

Provides REST API endpoints for customer management.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from oms.config.database import get_db_session
from oms.models.schemas import (
    CustomerCreate,
    CustomerResponse,
    ErrorResponse,
    PaginatedResponse,
)
from oms.services.customer_service import CustomerService

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def get_service(session=Depends(get_db_session)) -> CustomerService:
    """Dependency injection for CustomerService."""
    return CustomerService(session)


@router.post(
    "",
    response_model=CustomerResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create a new customer",
    description="Create a new customer account with the provided details.",
)
async def create_customer(
    customer_data: CustomerCreate,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    """
    Create a new customer.
    
    Args:
        customer_data: Customer creation data
        service: Customer service instance
        
    Returns:
        Created customer response
        
    Raises:
        HTTPException: If email already exists
    """
    try:
        return await service.create_customer(customer_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="Get all customers",
    description="Retrieve all customers with pagination support.",
)
async def get_all_customers(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CustomerService = Depends(get_service),
) -> PaginatedResponse:
    """
    Get all customers with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Customer service instance
        
    Returns:
        Paginated list of customers
    """
    customers = await service.get_all_customers(limit=limit, offset=offset)
    total = await service.repository.count()
    return PaginatedResponse(
        items=customers,
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if limit > 0 else 1,
    )


@router.get(
    "/active",
    response_model=List[CustomerResponse],
    summary="Get active customers",
    description="Retrieve all active customers.",
)
async def get_active_customers(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CustomerService = Depends(get_service),
) -> List[CustomerResponse]:
    """
    Get all active customers.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Customer service instance
        
    Returns:
        List of active customers
    """
    return await service.get_active_customers(limit=limit, offset=offset)


@router.get(
    "/search",
    response_model=List[CustomerResponse],
    summary="Search customers",
    description="Search customers by name pattern.",
)
async def search_customers(
    q: str = Query(..., min_length=1, description="Name pattern to search"),
    service: CustomerService = Depends(get_service),
) -> List[CustomerResponse]:
    """
    Search customers by name.
    
    Args:
        q: Name pattern to search for
        service: Customer service instance
        
    Returns:
        List of matching customers
    """
    return await service.search_customers(q)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get customer by ID",
    description="Retrieve a specific customer by their ID.",
)
async def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    """
    Get customer by ID.
    
    Args:
        customer_id: Customer ID
        service: Customer service instance
        
    Returns:
        Customer response
        
    Raises:
        HTTPException: If customer not found
    """
    customer = await service.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update customer",
    description="Update an existing customer's details.",
)
async def update_customer(
    customer_id: int,
    customer_data: CustomerCreate,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    """
    Update an existing customer.
    
    Args:
        customer_id: Customer ID
        customer_data: Updated customer data
        service: Customer service instance
        
    Returns:
        Updated customer response
        
    Raises:
        HTTPException: If customer not found
    """
    customer = await service.update_customer(customer_id, customer_data)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.delete(
    "/{customer_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
    summary="Delete customer (soft delete)",
    description="Soft delete a customer by setting is_active to False.",
)
async def delete_customer(
    customer_id: int,
    service: CustomerService = Depends(get_service),
) -> dict:
    """
    Delete a customer (soft delete).
    
    Args:
        customer_id: Customer ID
        service: Customer service instance
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: If customer not found
    """
    success = await service.delete_customer(customer_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"message": f"Customer {customer_id} deleted successfully"}
