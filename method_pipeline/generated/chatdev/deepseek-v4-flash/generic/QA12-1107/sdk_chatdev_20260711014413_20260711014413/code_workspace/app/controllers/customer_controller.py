"""
Customer REST controller.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
)
from app.services.customer_service import CustomerService


def create_customer_router(
    dep_service: Callable[[], CustomerService],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])

    @router.post("", response_model=CustomerResponse, status_code=201)
    async def create_customer(
        body: CustomerCreate,
        service: CustomerService = Depends(dep_service),
    ):
        return await service.create_customer(
            name=body.name,
            address=body.address,
            phone=body.phone,
            banking_details=body.banking_details,
            role=body.role,
        )

    @router.get("/{customer_id}", response_model=CustomerResponse)
    async def get_customer(
        customer_id: str,
        service: CustomerService = Depends(dep_service),
    ):
        customer = await service.get_customer(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    @router.get("", response_model=CustomerListResponse)
    async def list_customers(
        skip: int = 0,
        limit: int = 100,
        service: CustomerService = Depends(dep_service),
    ):
        customers, total = await service.list_customers(skip=skip, limit=limit)
        return CustomerListResponse(customers=customers, total=total)

    return router
