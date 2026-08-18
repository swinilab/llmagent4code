"""
Product service with business logic and validation
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from oms.repository.product_repository import ProductRepository
from oms.domain.models import Product, ProductCreate
from oms.infrastructure.exceptions import NotFoundException
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.database import transaction_session


class ProductService:
    """
    Product service implementing business logic
    Implements NFR 1.2 via cache integration
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ProductRepository(session)
        self.cache = MemoryCache.get_instance()
    
    async def get_by_id(self, product_id: str) -> Product:
        """Get product by ID with cache lookup"""
        # Try cache first (NFR 1.2)
        cached = await self.cache.get(f"product:{product_id}")
        if cached:
            return Product(**cached)
        
        # Fallback to database
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(f"Product {product_id} not found")
        
        # Populate cache
        await self.cache.set(f"product:{product_id}", product.model_dump())
        return product
    
    async def get_all(self) -> List[Product]:
        """Get all products"""
        return await self.repository.get_all()
    
    async def create(self, product: ProductCreate) -> Product:
        """Create new product"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            product_repo = ProductRepository(session)
            created = await product_repo.create(product)
            # Populate cache
            await self.cache.set(f"product:{created.id}", created.model_dump())
            return created
    
    async def update(self, product_id: str, product: ProductCreate) -> Product:
        """Update existing product"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            product_repo = ProductRepository(session)
            # Invalidate cache
            await self.cache.delete(f"product:{product_id}")
            
            updated = await product_repo.update(product_id, product)
            if not updated:
                raise NotFoundException(f"Product {product_id} not found")
            
            # Populate cache
            await self.cache.set(f"product:{product_id}", updated.model_dump())
            return updated
    
    async def delete(self, product_id: str) -> bool:
        """Delete product"""
        # Invalidate cache
        await self.cache.delete(f"product:{product_id}")
        return await self.repository.delete(product_id)
