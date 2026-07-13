from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models import Product
from app.schemas.product import ProductCreate, ProductUpdate

async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()

async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()

async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    db_obj = Product(**product_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_product(
    db: AsyncSession, db_obj: Product, obj_in: ProductUpdate
) -> Product:
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    obj = await get_product(db, product_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj