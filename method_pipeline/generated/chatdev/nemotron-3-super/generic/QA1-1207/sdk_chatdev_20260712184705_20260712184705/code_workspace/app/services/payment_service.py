from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import payment as crud_payment
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse

async def get_payment(db: AsyncSession, payment_id: int) -> Optional[PaymentResponse]:
    obj = await crud_payment.get_payment(db, payment_id)
    return PaymentResponse.from_orm(obj) if obj else None

async def get_payment_by_order(db: AsyncSession, order_id: int) -> Optional[PaymentResponse]:
    obj = await crud_payment.get_payment_by_order(db, order_id)
    return PaymentResponse.from_orm(obj) if obj else None

async def get_payments(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[PaymentResponse]:
    objs = await crud_payment.get_payments(db, skip, limit)
    return [PaymentResponse.from_orm(obj) for obj in objs]

async def create_payment(db: AsyncSession, payment_in: PaymentCreate) -> PaymentResponse:
    obj = await crud_payment.create_payment(db, payment_in)
    return PaymentResponse.from_orm(obj)

async def update_payment(
    db: AsyncSession, payment_id: int, payment_in: PaymentUpdate
) -> Optional[PaymentResponse]:
    obj = await crud_payment.get_payment(db, payment_id)
    if not obj:
        return None
    updated = await crud_payment.update_payment(db, obj, payment_in)
    return PaymentResponse.from_orm(updated)

async def delete_payment(db: AsyncSession, payment_id: int) -> bool:
    obj = await crud_payment.get_payment(db, payment_id)
    if not obj:
        return False
    await crud_payment.delete_payment(db, payment_id)
    return True