from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from app.db.models import Order, OrderItem
from app.schemas.order import OrderCreate, OrderUpdate, OrderItemCreate, OrderItemUpdate

async def get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()

async def get_orders(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Order]:
    result = await db.execute(select(Order).offset(skip).limit(limit))
    return result.scalars().all()

async def create_order_with_items(
    db: AsyncSession, order_in: OrderCreate
) -> Order:
    # Create order
    order_data = order_in.dict(exclude={"items"})
    db_order = Order(**order_data)
    db.add(db_order)
    await db.flush()  # get id
    # Create items
    total = 0
    for item_in in order_in.items:
        item_data = item_in.dict()
        item = OrderItem(**item_data, order_id=db_order.id)
        db.add(item)
        total += item_data["quantity"] * item_data["unit_price"]
    db_order.total_amount = total
    await db.commit()
    await db.refresh(db_order)
    # reload with items
    result = await db.execute(
        select(Order).where(Order.id == db_order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()

async def update_order(
    db: AsyncSession, db_obj: Order, order_in: OrderUpdate
) -> Order:
    update_data = order_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    obj = await get_order(db, order_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj

# OrderItem CRUD
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