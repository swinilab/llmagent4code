"""
Service layer for Product entity.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Business logic for product operations."""

    @staticmethod
    async def create(db: AsyncSession, data: ProductCreate) -> Product:
        """Create a new product."""
        product = Product(**data.model_dump())
        db.add(product)
        await db.flush()
        return product

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: str) -> Optional[Product]:
        """Retrieve a product by ID."""
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
        """List products with pagination."""
        result = await db.execute(
            select(Product).offset(skip).limit(limit).order_by(Product.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def search(db: AsyncSession, query: str, skip: int = 0, limit: int = 20) -> List[Product]:
        """Search products by description (case-insensitive LIKE)."""
        stmt = (
            select(Product)
            .where(Product.description.ilike(f"%{query}%"))
            .offset(skip)
            .limit(limit)
            .order_by(Product.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, product_id: str, data: ProductUpdate) -> Optional[Product]:
        """Update a product."""
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await db.flush()
        # Refresh to load server-side defaults (updated_at)
        await db.refresh(product)
        return product

    @staticmethod
    async def delete(db: AsyncSession, product_id: str) -> bool:
        """Delete a product by ID."""
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return False
        await db.delete(product)
        await db.flush()
        return True
