"""
Customer controller — CRUD endpoints for customer management.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.enums import UserRole
from oms.domain.models import Customer
from oms.infrastructure.database import get_db
from oms.infrastructure.entities import CustomerModel
from oms.repositories.customer_repo import CustomerRepository

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


class CreateCustomerRequest(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole = UserRole.CUSTOMER


class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: str
    order_history: list[str]


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    req: CreateCustomerRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Create a new customer."""
    repo = CustomerRepository(db)
    model = CustomerModel(
        name=req.name,
        address=req.address,
        phone=req.phone,
        banking_details=req.banking_details,
        role=req.role,
        order_history=[],
    )
    await repo.save(model)
    await db.commit()
    return CustomerResponse(
        id=str(model.id),
        name=model.name,
        address=model.address,
        phone=model.phone,
        banking_details=model.banking_details,
        role=model.role.value,
        order_history=[],
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Get customer by ID."""
    repo = CustomerRepository(db)
    model = await repo.get(customer_id)
    if not model:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse(
        id=str(model.id),
        name=model.name,
        address=model.address,
        phone=model.phone,
        banking_details=model.banking_details,
        role=model.role.value,
        order_history=[str(oid) for oid in (model.order_history or [])],
    )


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    """List all customers."""
    from sqlalchemy import select
    repo = CustomerRepository(db)
    stmt = select(CustomerModel)
    result = await db.execute(stmt)
    models = list(result.scalars().all())
    return [
        CustomerResponse(
            id=str(m.id),
            name=m.name,
            address=m.address,
            phone=m.phone,
            banking_details=m.banking_details,
            role=m.role.value,
            order_history=[str(oid) for oid in (m.order_history or [])],
        )
        for m in models
    ]
