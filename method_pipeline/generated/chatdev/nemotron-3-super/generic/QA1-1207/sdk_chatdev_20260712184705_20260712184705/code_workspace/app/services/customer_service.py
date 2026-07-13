from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import customer as crud_customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

async def get_customer(db: AsyncSession, customer_id: int) -> Optional[CustomerResponse]:
    obj = await crud_customer.get_customer(db, customer_id)
    return CustomerResponse.from_orm(obj) if obj else None

async def get_customers(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[CustomerResponse]:
    objs = await crud_customer.get_customers(db, skip, limit)
    return [CustomerResponse.from_orm(obj) for obj in objs]

async def create_customer(db: AsyncSession, customer_in: CustomerCreate) -> CustomerResponse:
    obj = await crud_customer.create_customer(db, customer_in)
    return CustomerResponse.from_orm(obj)

async def update_customer(
    db: AsyncSession, customer_id: int, customer_in: CustomerUpdate
) -> Optional[CustomerResponse]:
    obj = await crud_customer.get_customer(db, customer_id)
    if not obj:
        return None
    updated = await crud_customer.update_customer(db, obj, customer_in)
    return CustomerResponse.from_orm(updated)

async def delete_customer(db: AsyncSession, customer_id: int) -> bool:
    obj = await crud_customer.get_customer(db, customer_id)
    if not obj:
        return False
    await crud_customer.delete_customer(db, customer_id)
    return True