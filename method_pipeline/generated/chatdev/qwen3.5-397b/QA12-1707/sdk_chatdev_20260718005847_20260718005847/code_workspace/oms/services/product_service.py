"""
Product service for business logic operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms.models.product import Product, ProductCreate, ProductUpdate, ProductResponse
from oms.repositories.product_repository import ProductRepository


class ProductService:
    """
    Service for Product business logic.
    Handles validation, business rules, and orchestration.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ProductRepository(session)
    
    async def get_product(self, product_id: int) -> Optional[ProductResponse]:
        """Get a product by ID."""
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        return ProductResponse.model_validate(product)
    
    async def search_products(self, query: str, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Search products by name or description."""
        products = await self.repository.search(query, skip=skip, limit=limit)
        return [ProductResponse.model_validate(p) for p in products]
    
    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Get all products with pagination."""
        products = await self.repository.get_all(skip=skip, limit=limit)
        return [ProductResponse.model_validate(p) for p in products]
    
    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Create a new product."""
        product = await self.repository.create(product_data)
        return ProductResponse.model_validate(product)
    
    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[ProductResponse]:
        """Update an existing product."""
        product = await self.repository.update(product_id, product_data)
        if not product:
            return None
        return ProductResponse.model_validate(product)
    
    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        return await self.repository.delete(product_id)
    
    async def get_product_count(self) -> int:
        """Get total number of products."""
        return await self.repository.count()
    
    async def check_stock(self, product_id: int, quantity: int) -> bool:
        """Check if sufficient stock is available."""
        product = await self.repository.get_by_id(product_id)
        if not product:
            return False
        return product.stock_quantity >= quantity
    
    async def reserve_stock(self, product_id: int, quantity: int) -> bool:
        """Reserve stock for an order."""
        product = await self.repository.update_stock(product_id, -quantity)
        return product is not None
    
    async def release_stock(self, product_id: int, quantity: int) -> bool:
        """Release reserved stock."""
        product = await self.repository.update_stock(product_id, quantity)
        return product is not None
