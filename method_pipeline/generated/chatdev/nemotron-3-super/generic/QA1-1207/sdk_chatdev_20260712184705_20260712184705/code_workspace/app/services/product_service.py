from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import product as crud_product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

async def get_product(db: AsyncSession, product_id: int) -> Optional[ProductResponse]:
    obj = await crud_product.get_product(db, product_id)
    return ProductResponse.from_orm(obj) if obj else None

async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
    objs = await crud_product.get_products(db, skip, limit)
    return [ProductResponse.from_orm(obj) for obj in objs]

async def create_product(db: AsyncSession, product_in: ProductCreate) -> ProductResponse:
    obj = await crud_product.create_product(db, product_in)
    return ProductResponse.from_orm(obj)

async def update_product(
    db: AsyncSession, product_id: int, product_in: ProductUpdate
) -> Optional[ProductResponse]:
    obj = await crud_product.get_product(db, product_id)
    if not obj:
        return None
    updated = await crud_product.update_product(db, obj, product_in)
    return ProductResponse.from_orm(updated)

async def delete_product(db: AsyncSession, product_id: int) -> bool:
    obj = await crud_product.get_product(db, product_id)
    if not obj:
        return False
    await crud_product.delete_product(db, product_id)
    return True