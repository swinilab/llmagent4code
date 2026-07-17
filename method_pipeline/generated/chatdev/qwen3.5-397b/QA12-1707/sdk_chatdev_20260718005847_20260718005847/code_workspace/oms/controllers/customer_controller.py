"""
Customer REST API controller.
Handles HTTP requests for customer operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms.config.database import get_db
from oms.models.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from oms.services.customer_service import CustomerService

customer_router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@customer_router.get("", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get all customers with pagination."""
    service = CustomerService(db)
    return await service.get_all_customers(skip=skip, limit=limit)


@customer_router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    """Get a customer by ID."""
    service = CustomerService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@customer_router.get("/email/{email}", response_model=CustomerResponse)
async def get_customer_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Get a customer by email."""
    service = CustomerService(db)
    customer = await service.get_customer_by_email(email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@customer_router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(customer_data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new customer."""
    service = CustomerService(db)
    try:
        return await service.create_customer(customer_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@customer_router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: int, customer_data: CustomerUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing customer."""
    service = CustomerService(db)
    customer = await service.update_customer(customer_id, customer_data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@customer_router.delete("/{customer_id}", status_code=204)
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a customer."""
    service = CustomerService(db)
    deleted = await service.delete_customer(customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None


@customer_router.get("/count")
async def get_customer_count(db: AsyncSession = Depends(get_db)):
    """Get total number of customers."""
    service = CustomerService(db)
    return {"count": await service.get_customer_count()}
