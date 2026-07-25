"""
Product service with business logic
"""
from typing import List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repository import ProductRepository
from app.models.product import Product, Price
from app.db.tables import ProductTable


class ProductService:
    """Service layer for Product operations"""
    
    def __init__(self, session: AsyncSession):
        self.repository = ProductRepository(session)
    
    async def create_product(
        self,
        description: str,
        amount: Decimal,
        currency: str,
    ) -> Product:
        """Create a new product"""
        entity = await self.repository.create_product(
            description=description,
            price_amount=amount,
            price_currency=currency,
        )
        return self._to_model(entity)
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        entity = await self.repository.get_by_id(product_id)
        return self._to_model(entity) if entity else None
    
    async def get_all_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Get all products"""
        entities = await self.repository.get_all(limit, offset)
        return [self._to_model(e) for e in entities]
    
    def _to_model(self, entity: ProductTable) -> Product:
        """Convert table entity to domain model"""
        return Product(
            id=entity.id,
            description=entity.description,
            price=Price(
                amount=Decimal(str(entity.price_amount)),
                currency=entity.price_currency,
            ),
        )
