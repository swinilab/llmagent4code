from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

async def get_payment(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()

async def get_payment_by_order(db: AsyncSession, order_id: int) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.order_id == order_id)
    )
    return result.scalar_one_or_none()

async def create_payment(db: AsyncSession, payment_in: PaymentCreate) -> Payment:
    db_obj = Payment(**payment_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_payment(
    db: AsyncSession, db_obj: Payment, payment_in: PaymentUpdate
) -> Payment:
    update_data = payment_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_payment(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    obj = await get_payment(db, payment_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj

async def get_payments(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Payment]:
    result = await db.execute(select(Payment).offset(skip).limit(limit))
    return result.scalars().all()