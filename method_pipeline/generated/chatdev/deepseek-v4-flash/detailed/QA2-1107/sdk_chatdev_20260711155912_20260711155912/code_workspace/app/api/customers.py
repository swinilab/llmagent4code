"""
Customer API endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories import CustomerRepository
from app.core.exceptions import NotFoundError
from app.domain.models import Customer
from app.domain.schemas import CustomerCreate, CustomerResponse
from app.infrastructure.database import get_db_session

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Customer:
    repo = CustomerRepository(session)
    customer = Customer(
        name=data.name,
        address=data.address,
        phone=data.phone,
        banking_details=data.banking_details,
        role=data.role,
    )
    return await repo.create(customer)


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    session: AsyncSession = Depends(get_db_session),
) -> list[Customer]:
    repo = CustomerRepository(session)
    return list(await repo.list_all())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Customer:
    repo = CustomerRepository(session)
    customer = await repo.get(customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer
