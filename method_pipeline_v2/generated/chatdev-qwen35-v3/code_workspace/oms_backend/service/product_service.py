"""
Product service with business logic
Implements NFR 2.4 (transactions) via async session management
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms_backend.repository.product_repository import ProductRepository
from oms_backend.domain.models import Product
from oms_backend.domain.schemas import ProductCreate


class ProductService:
    """Service for Product business logic"""
    
    def __init__(self, session: AsyncSession):
        self.repository = ProductRepository(session)
        self.session = session
    
    async def create_product(self, data: ProductCreate) -> Product:
        """Create a new product with transactional semantics (NFR 2.4)"""
        product = await self.repository.create(data)
        return product
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID with cache check (NFR 1.2)"""
        from oms_backend.repository.base import db
        cache_key = f"product:{product_id}"
        cached = db.get_cached(cache_key)
        if cached:
            return cached
        
        product = await self.repository.get_by_id(product_id)
        if product:
            db.set_cached(cache_key, product)
        return product
    
    async def get_all_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Get all products"""
        return await self.repository.get_all(limit, offset)
    
    async def update_product(self, product_id: str, data: dict) -> Optional[Product]:
        """Update product with cache invalidation (NFR 1.2)"""
        from oms_backend.repository.base import db
        product = await self.repository.update(product_id, data)
        if product:
            db.set_cached(f"product:{product_id}", product)
        return product
