"""
Product repository for database operations
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.tables import ProductTable
from app.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[ProductTable]):
    """Repository for Product entity"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ProductTable)
    
    async def get_by_id(self, id: str) -> Optional[ProductTable]:
        """Get product by ID"""
        return await self.get(id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ProductTable]:
        """Get all products"""
        return await self.list_all(limit, offset)
    
    async def create_product(
        self,
        description: str,
        price_amount: Decimal,
        price_currency: str,
    ) -> ProductTable:
        """Create a new product"""
        from app.db.tables import generate_uuid
        entity = ProductTable(
            id=generate_uuid(),
            description=description,
            price_amount=price_amount,
            price_currency=price_currency,
        )
        return await self.create(entity)
