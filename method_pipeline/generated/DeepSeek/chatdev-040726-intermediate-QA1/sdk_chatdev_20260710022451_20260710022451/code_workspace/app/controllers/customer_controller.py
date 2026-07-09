"""
Customer REST controller.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import CustomerCreate, CustomerResponse, PaginatedResponse
from app.infrastructure.database import get_db
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db),
):
    svc = CustomerService(session)
    customer = await svc.create_customer(data)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = CustomerService(session)
    return await svc.get_customer(customer_id)


@router.get("", response_model=PaginatedResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    svc = CustomerService(session)
    items, total = await svc.list_customers(page, page_size)
    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
