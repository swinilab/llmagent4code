from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import customer_service
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter()

@router.get("/", response_model=List[CustomerResponse])
async def read_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    customers = await customer_service.get_customers(db, skip=skip, limit=limit)
    return customers

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.create_customer(db, customer_in)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def read_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
):
    customer = await customer_service.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    customer = await customer_service.update_customer(db, customer_id, customer_in)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db,
):
    success = await customer_service.delete_customer(db, customer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None