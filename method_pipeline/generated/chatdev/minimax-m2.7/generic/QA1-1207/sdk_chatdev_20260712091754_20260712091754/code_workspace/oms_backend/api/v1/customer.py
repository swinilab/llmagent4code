"""
CustomerController — REST endpoints for customer management.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.db.connection import get_session
from oms_backend.schemas.domain import Customer, CustomerCreate, CustomerUpdate, paginate
from oms_backend.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Register a new customer."""
    svc = CustomerService(session)
    return await svc.create(data)


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a customer by ID."""
    svc = CustomerService(session)
    customer = await svc.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("", response_model=dict)
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all customers (paginated)."""
    svc = CustomerService(session)
    customers, total = await svc.list(page=page, page_size=page_size)
    return paginate(
        [Customer.model_validate(c) for c in customers],
        total=total, page=page, page_size=page_size
    ).model_dump()


@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update customer details."""
    svc = CustomerService(session)
    updated = await svc.update(customer_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(
    customer_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Soft-delete (deactivate) a customer."""
    svc = CustomerService(session)
    ok = await svc.deactivate(customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")
