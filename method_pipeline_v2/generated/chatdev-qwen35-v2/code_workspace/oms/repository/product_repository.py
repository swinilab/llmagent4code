"""
Product repository with validation and business logic
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from oms.infrastructure.database import ProductModel
from oms.domain.models import Product, ProductCreate
from oms.infrastructure.exceptions import NotFoundException

class ProductRepository:
    """
    Product repository implementing data access with validation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._model_class = ProductModel
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == product_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)
    
    async def get_all(self) -> List[Product]:
        """Get all products"""
        result = await self.session.execute(select(self._model_class))
        models = list(result.scalars().all())
        return [self._to_domain(m) for m in models]
    
    async def create(self, product: ProductCreate) -> Product:
        """Create new product"""
        model = ProductModel(
            description=product.description,
            price_amount=float(product.price.amount),
            price_currency=product.price.currency
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def update(self, product_id: str, product: ProductCreate) -> Optional[Product]:
        """Update existing product"""
        model = await self._get_model(product_id)
        if not model:
            return None
        
        model.description = product.description
        model.price_amount = float(product.price.amount)
        model.price_currency = product.price.currency
        
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def delete(self, product_id: str) -> bool:
        """Delete product"""
        model = await self._get_model(product_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def _get_model(self, product_id: str) -> Optional[ProductModel]:
        """Get model by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == product_id)
        )
        return result.scalar_one_or_none()
    
    def _to_domain(self, model: ProductModel) -> Product:
        """Convert model to domain object"""
        return Product(
            id=model.id,
            description=model.description,
            price={
                'amount': Decimal(str(model.price_amount)),
                'currency': model.price_currency
            }
        )
