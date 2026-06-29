"""
Customer Routes - API endpoints for Customer operations.
Defines RESTful endpoints for customer management.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import get_session
from controllers.customer_controller import CustomerController
from shared.models import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
    CustomerListResponse,
    APIResponse,
)

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all customers with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    """
    controller = CustomerController(db)
    return await controller.get_all_customers(skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific customer by ID.
    
    - **customer_id**: The unique customer identifier
    """
    controller = CustomerController(db)
    customer = await controller.get_customer(customer_id)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.get("/email/{email}", response_model=Customer)
async def get_customer_by_email(
    email: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a customer by email address.
    
    - **email**: Customer email address
    """
    controller = CustomerController(db)
    customer = await controller.get_customer_by_email(email)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.post("", response_model=Customer, status_code=201)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new customer.
    
    - **name**: Customer full name
    - **address**: Customer address
    - **phone**: Customer phone number
    - **email**: Customer email address
    - **banking_details**: Optional banking information
    - **role**: User role (default: customer)
    """
    controller = CustomerController(db)
    
    # Check if email already exists
    existing = await controller.get_customer_by_email(customer_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return await controller.create_customer(customer_data)


@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing customer.
    
    - **customer_id**: The unique customer identifier
    - **name**: Optional new name
    - **address**: Optional new address
    - **phone**: Optional new phone
    - **email**: Optional new email
    - **banking_details**: Optional new banking details
    - **role**: Optional new role
    """
    controller = CustomerController(db)
    
    customer = await controller.update_customer(customer_id, customer_data)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.delete("/{customer_id}", response_model=APIResponse)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a customer.
    
    - **customer_id**: The unique customer identifier
    """
    controller = CustomerController(db)
    
    success = await controller.delete_customer(customer_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return APIResponse(success=True, message="Customer deleted successfully")
