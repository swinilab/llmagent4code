"""
Product repository with CRUD operations
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.domain.models import Product
from oms_backend.domain.schemas import ProductCreate


class ProductRepository:
    """Repository for Product entity operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: ProductCreate) -> Product:
        """Create a new product"""
        product = Product(
            description=data.description,
            price_amount=data.price.amount,
            price_currency=data.price.currency
        )
        self.session.add(product)
        await self.session.flush()
        return product
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Get all products with pagination"""
        result = await self.session.execute(
            select(Product).offset(offset).limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, product_id: str, data: dict) -> Optional[Product]:
        """Update product fields"""
        await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(**data, updated_at=datetime.utcnow())
        )
        return await self.get_by_id(product_id)
    
    async def delete(self, product_id: str) -> bool:
        """Delete product"""
        product = await self.get_by_id(product_id)
        if product:
            await self.session.delete(product)
            return True
        return False
