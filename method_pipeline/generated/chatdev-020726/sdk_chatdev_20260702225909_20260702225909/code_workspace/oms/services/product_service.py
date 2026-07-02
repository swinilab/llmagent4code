"""
Product service for product-related business logic.
"""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Product
from oms.models.schemas import ProductCreate, ProductResponse
from oms.repositories.product_repository import ProductRepository


class ProductService:
    """
    Service for managing product operations.
    
    Handles business logic for product creation, retrieval, inventory management,
    and product search functionality.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize product service.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.repository = ProductRepository(session)
        self.session = session
    
    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """
        Create a new product.
        
        Args:
            product_data: Product creation data
            
        Returns:
            Created product response
        """
        product = Product(
            name=product_data.name,
            description=product_data.description,
            base_price=product_data.base_price,
            currency=product_data.currency,
            stock_quantity=product_data.stock_quantity,
            is_available=product_data.stock_quantity > 0,
        )
        created = await self.repository.create(product)
        return ProductResponse.model_validate(created)
    
    async def get_product(self, product_id: int) -> Optional[ProductResponse]:
        """
        Get product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product response or None if not found
        """
        product = await self.repository.get(product_id)
        if product is None:
            return None
        return ProductResponse.model_validate(product)
    
    async def get_all_products(
        self, limit: int = 100, offset: int = 0
    ) -> List[ProductResponse]:
        """
        Get all products with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of product responses
        """
        products = await self.repository.get_all(limit=limit, offset=offset)
        return [ProductResponse.model_validate(p) for p in products]
    
    async def get_available_products(
        self, limit: int = 100, offset: int = 0
    ) -> List[ProductResponse]:
        """
        Get all available products (in stock).
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of available product responses
        """
        products = await self.repository.get_available_products(limit=limit, offset=offset)
        return [ProductResponse.model_validate(p) for p in products]
    
    async def search_products(self, name_pattern: str) -> List[ProductResponse]:
        """
        Search products by name.
        
        Args:
            name_pattern: Name pattern to search for
            
        Returns:
            List of matching product responses
        """
        products = await self.repository.search_by_name(name_pattern)
        return [ProductResponse.model_validate(p) for p in products]
    
    async def get_products_by_price_range(
        self, min_price: Decimal, max_price: Decimal
    ) -> List[ProductResponse]:
        """
        Get products within a price range.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            List of products within the price range
        """
        products = await self.repository.get_products_by_price_range(
            float(min_price), float(max_price)
        )
        return [ProductResponse.model_validate(p) for p in products]
    
    async def update_product(
        self, product_id: int, product_data: ProductCreate
    ) -> Optional[ProductResponse]:
        """
        Update an existing product.
        
        Args:
            product_id: Product ID
            product_data: Updated product data
            
        Returns:
            Updated product response or None if not found
        """
        product = await self.repository.get(product_id)
        if product is None:
            return None
        
        product.name = product_data.name
        product.description = product_data.description
        product.base_price = product_data.base_price
        product.currency = product_data.currency
        product.stock_quantity = product_data.stock_quantity
        product.is_available = product_data.stock_quantity > 0
        
        updated = await self.repository.update(product)
        return ProductResponse.model_validate(updated)
    
    async def update_stock(
        self, product_id: int, quantity_change: int
    ) -> Optional[ProductResponse]:
        """
        Update product stock quantity.
        
        Args:
            product_id: Product ID
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated product response or None if not found
        """
        product = await self.repository.update_stock(product_id, quantity_change)
        if product is None:
            return None
        return ProductResponse.model_validate(product)
    
    async def delete_product(self, product_id: int) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(product_id)
    
    async def check_availability(self, product_id: int, quantity: int) -> bool:
        """
        Check if product has sufficient stock.
        
        Args:
            product_id: Product ID
            quantity: Required quantity
            
        Returns:
            True if available, False otherwise
        """
        product = await self.repository.get(product_id)
        if product is None:
            return False
        return product.is_available and product.stock_quantity >= quantity
