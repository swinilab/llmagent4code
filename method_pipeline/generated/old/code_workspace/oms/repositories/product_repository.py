"""
Product repository for product-specific database operations.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Product
from oms.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """
    Repository for Product entity operations.
    
    Extends BaseRepository with product-specific queries including search and filtering.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize product repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(Product, session)
    
    async def get_available_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """
        Get all available products with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of available product instances
        """
        query = select(Product).where(
            Product.is_available == True
        ).where(
            Product.stock_quantity > 0
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_by_name(self, name_pattern: str, limit: int = 50) -> List[Product]:
        """
        Search products by name pattern.
        
        Args:
            name_pattern: Name pattern to search for
            limit: Maximum number of results
            
        Returns:
            List of matching product instances
        """
        query = select(Product).where(
            Product.name.ilike(f"%{name_pattern}%")
        ).where(
            Product.is_available == True
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_products_by_price_range(
        self, min_price: float, max_price: float, limit: int = 100
    ) -> List[Product]:
        """
        Get products within a price range.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            limit: Maximum number of results
            
        Returns:
            List of products within the price range
        """
        query = select(Product).where(
            Product.base_price >= min_price
        ).where(
            Product.base_price <= max_price
        ).where(
            Product.is_available == True
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """
        Update product stock quantity.
        
        Args:
            product_id: Product ID
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated product or None if not found
        """
        product = await self.get(product_id)
        if product is None:
            return None
        product.stock_quantity = max(0, product.stock_quantity + quantity_change)
        await self.session.flush()
        await self.session.refresh(product)
        return product
