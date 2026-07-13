from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

async def get_customer(db: AsyncSession, customer_id: int) -> Optional[Customer]:
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()

async def get_customers(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Customer]:
    result = await db.execute(select(Customer).offset(skip).limit(limit))
    return result.scalars().all()

async def create_customer(db: AsyncSession, customer_in: CustomerCreate) -> Customer:
    db_obj = Customer(**customer_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_customer(
    db: AsyncSession, db_obj: Customer, customer_in: CustomerUpdate
) -> Customer:
    update_data = customer_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_customer(db: AsyncSession, customer_id: int) -> Optional[Customer]:
    obj = await get_customer(db, customer_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj