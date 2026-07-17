"""
Product repository for data access operations.
"""

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms.models.product import Product, ProductCreate, ProductUpdate


class ProductRepository:
    """
    Repository for Product entity operations.
    Provides CRUD operations with async support.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get a product by ID."""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Product]:
        """Get a product by name."""
        result = await self.session.execute(
            select(Product).where(Product.name == name)
        )
        return result.scalar_one_or_none()
    
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """Search products by name or description."""
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(Product)
            .where(
                (Product.name.ilike(search_pattern)) |
                (Product.description.ilike(search_pattern))
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get all products with pagination."""
        result = await self.session.execute(
            select(Product).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, product_data: ProductCreate) -> Product:
        """Create a new product."""
        product = Product(**product_data.model_dump())
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product
    
    async def update(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Update an existing product."""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await self.session.flush()
        await self.session.refresh(product)
        return product
    
    async def delete(self, product_id: int) -> bool:
        """Delete a product by ID."""
        product = await self.get_by_id(product_id)
        if not product:
            return False
        
        await self.session.delete(product)
        await self.session.flush()
        return True
    
    async def count(self) -> int:
        """Get total number of products."""
        result = await self.session.execute(select(func.count()).select_from(Product))
        return result.scalar() or 0
    
    async def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """Update product stock quantity."""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        product.stock_quantity += quantity_change
        await self.session.flush()
        await self.session.refresh(product)
        return product
