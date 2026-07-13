from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud, services
from app.database import get_db

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=schemas.Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: schemas.CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new customer.
    """
    customer = await crud.get_customer_by_email(db, email=customer_in.email)
    if customer:
        raise HTTPException(
            status_code=400,
            detail="Customer with this email already exists",
        )
    return await crud.create_customer(db, customer_in=customer_in)


@router.get("/", response_model=List[schemas.Customer])
async def read_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve customers.
    """
    customers = await crud.get_customers(db, skip=skip, limit=limit)
    return customers


@router.get("/{customer_id}", response_model=schemas.Customer)
async def read_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific customer by ID.
    """
    customer = await crud.get_customer(db, customer_id=customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=schemas.Customer)
async def update_customer(
    customer_id: int,
    customer_in: schemas.CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a customer.
    """
    customer = await crud.update_customer(
        db, customer_id=customer_id, customer_in=customer_in
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", response_model=schemas.Customer)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a customer.
    """
    customer = await crud.delete_customer(db, customer_id=customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer