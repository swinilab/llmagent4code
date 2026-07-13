from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.services.customer import CustomerService
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerInDB
from app.database import get_db

router = APIRouter()

def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    repo = CustomerRepository(db)
    return CustomerService(repo)

@router.post("/", response_model=CustomerInDB, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    service: CustomerService = Depends(get_customer_service)
):
    return service.create(customer_in)

@router.get("/{customer_id}", response_model=CustomerInDB)
async def read_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service)
):
    customer = service.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.get("/", response_model=List[CustomerInDB])
async def read_customers(
    skip: int = 0,
    limit: int = 100,
    service: CustomerService = Depends(get_customer_service)
):
    return service.get_multi(skip=skip, limit=limit)

@router.put("/{customer_id}", response_model=CustomerInDB)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service)
):
    customer = service.update(customer_id, customer_in)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.delete("/{customer_id}", response_model=CustomerInDB)
async def delete_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service)
):
    customer = service.delete(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer