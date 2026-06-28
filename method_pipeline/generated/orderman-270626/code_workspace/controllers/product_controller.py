"""
Product Controller - Handles HTTP request/response for Product operations.
Coordinates between routes and services.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductListResponse,
)
from services.product_service import ProductService


class ProductController:
    """Controller class for Product HTTP operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the controller with a database session."""
        self.service = ProductService(db_session)

    async def get_product(self, product_id: int) -> Optional[Product]:
        """
        Get a single product by ID.
        
        Args:
            product_id: The unique product ID
            
        Returns:
            Product object if found, None otherwise
        """
        return await self.service.get_product_by_id(product_id)

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """
        Get a product by SKU.
        
        Args:
            sku: Product SKU
            
        Returns:
            Product object if found, None otherwise
        """
        return await self.service.get_product_by_sku(sku)

    async def get_all_products(
        self, skip: int = 0, limit: int = 100
    ) -> ProductListResponse:
        """
        Get all products with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            ProductListResponse with products and total count
        """
        products = await self.service.get_all_products(skip=skip, limit=limit)
        total = await self.service.get_product_count()
        return ProductListResponse(products=products, total=total)

    async def search_products(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> ProductListResponse:
        """
        Search products by name or description.
        
        Args:
            search_term: Search term to match
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            ProductListResponse with matching products and total count
        """
        products = await self.service.search_products(
            search_term=search_term, skip=skip, limit=limit
        )
        return ProductListResponse(products=products, total=len(products))

    async def create_product(self, product_data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            product_data: ProductCreate object with product information
            
        Returns:
            Created Product object
        """
        return await self.service.create_product(product_data)

    async def update_product(
        self, product_id: int, product_data: ProductUpdate
    ) -> Optional[Product]:
        """
        Update an existing product.
        
        Args:
            product_id: The unique product ID
            product_data: ProductUpdate object with updated information
            
        Returns:
            Updated Product object if found, None otherwise
        """
        return await self.service.update_product(product_id, product_data)

    async def update_stock(
        self, product_id: int, quantity_change: int
    ) -> Optional[Product]:
        """
        Update product stock quantity.
        
        Args:
            product_id: The unique product ID
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated Product object if found, None otherwise
        """
        return await self.service.update_stock(product_id, quantity_change)

    async def delete_product(self, product_id: int) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: The unique product ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return await self.service.delete_product(product_id)
