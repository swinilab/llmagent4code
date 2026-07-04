"""Customer REST controller — v1 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.models import Customer
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/v1/customers", tags=["Customers"])


@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(body: Customer, db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    return await svc.create_customer(body)


@router.get("", response_model=list[Customer])
async def list_customers(db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    return await svc.list_customers()


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    customer = await svc.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer