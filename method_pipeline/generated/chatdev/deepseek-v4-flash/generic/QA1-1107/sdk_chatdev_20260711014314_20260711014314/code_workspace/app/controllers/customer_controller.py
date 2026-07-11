"""
REST controller for Customer entity.
Provides CRUD endpoints under /api/v1/customers.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new customer."""
    customer = await CustomerService.create(db, data)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a customer by ID."""
    customer = await CustomerService.get_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/", response_model=List[CustomerRead])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List customers with pagination."""
    customers = await CustomerService.get_all(db, skip=skip, limit=limit)
    return customers


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(customer_id: str, data: CustomerUpdate, db: AsyncSession = Depends(get_db)):
    """Update a customer's details."""
    customer = await CustomerService.update(db, customer_id, data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a customer by ID."""
    deleted = await CustomerService.delete(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
