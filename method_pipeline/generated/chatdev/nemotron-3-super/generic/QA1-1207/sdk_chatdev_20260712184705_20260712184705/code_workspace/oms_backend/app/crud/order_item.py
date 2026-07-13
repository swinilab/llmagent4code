from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from oms_backend.app.db.models import OrderItem
from oms_backend.app.schemas.order import OrderItemCreate, OrderItemUpdate


async def get_order_item(db: AsyncSession, item_id: int) -> Optional[OrderItem]:
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def get_order_items_by_order(db: AsyncSession, order_id: int) -> List[OrderItem]:
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    return result.scalars().all()


async def create_order_item(db: AsyncSession, item_in: OrderItemCreate) -> OrderItem:
    db_obj = OrderItem(**item_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_order_item(
    db: AsyncSession, db_obj: OrderItem, item_in: OrderItemUpdate
) -> OrderItem:
    update_data = item_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_order_item(db: AsyncSession, item_id: int) -> Optional[OrderItem]:
    obj = await get_order_item(db, item_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj