"""
Customer REST controller.

Endpoints:
  POST   /api/v1/customers          — create customer
  GET    /api/v1/customers          — list customers
  GET    /api/v1/customers/{id}     — get customer
  PATCH  /api/v1/customers/{id}     — update customer
  DELETE /api/v1/customers/{id}     — delete customer
  GET    /api/v1/customers/search   — search by name
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from src.services.customer import CustomerService

router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(payload: CustomerCreate, session: AsyncSession = Depends(get_session)):
    """Register a new customer."""
    svc = CustomerService(session)
    customer = await svc.create(payload)
    return customer


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all customers with pagination."""
    svc = CustomerService(session)
    return await svc.list_all(limit=limit, offset=offset)


@router.get("/search", response_model=list[CustomerResponse])
async def search_customers(
    q: str = Query(..., min_length=1, description="Name fragment to search"),
    session: AsyncSession = Depends(get_session),
):
    """Search customers by name fragment."""
    svc = CustomerService(session)
    return await svc.search(q)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve a customer by ID."""
    svc = CustomerService(session)
    return await svc.get(customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Partially update a customer."""
    svc = CustomerService(session)
    return await svc.update(customer_id, payload)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(customer_id: str, session: AsyncSession = Depends(get_session)):
    """Remove a customer."""
    svc = CustomerService(session)
    await svc.delete(customer_id)
