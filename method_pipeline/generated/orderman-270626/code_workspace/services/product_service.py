"""
Product Service - Business logic for Product operations.
Handles all product-related business operations.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import ProductModel
from shared.models import Product, ProductCreate, ProductUpdate


class ProductService:
    """Service class for Product business operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db_session

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get a product by its unique identifier.
        
        Args:
            product_id: The unique product ID
            
        Returns:
            Product object if found, None otherwise
        """
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if product:
            return self._to_domain_model(product)
        return None

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """
        Get a product by its SKU.
        
        Args:
            sku: Product SKU
            
        Returns:
            Product object if found, None otherwise
        """
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.sku == sku)
        )
        product = result.scalar_one_or_none()
        
        if product:
            return self._to_domain_model(product)
        return None

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """
        Get all products with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Product objects
        """
        result = await self.db.execute(
            select(ProductModel)
            .offset(skip)
            .limit(limit)
        )
        products = result.scalars().all()
        return [self._to_domain_model(p) for p in products]

    async def get_product_count(self) -> int:
        """
        Get the total number of products.
        
        Returns:
            Total count of products
        """
        result = await self.db.execute(
            select(func.count()).select_from(ProductModel)
        )
        return result.scalar() or 0

    async def search_products(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """
        Search products by name or description.
        
        Args:
            search_term: Search term to match
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching Product objects
        """
        search_pattern = f"%{search_term}%"
        result = await self.db.execute(
            select(ProductModel)
            .where(
                (ProductModel.name.ilike(search_pattern)) |
                (ProductModel.description.ilike(search_pattern))
            )
            .offset(skip)
            .limit(limit)
        )
        products = result.scalars().all()
        return [self._to_domain_model(p) for p in products]

    async def create_product(self, product_data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            product_data: ProductCreate object with product information
            
        Returns:
            Created Product object
        """
        product = ProductModel(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            sku=product_data.sku,
            stock_quantity=product_data.stock_quantity,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        
        return self._to_domain_model(product)

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
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return None
        
        # Update fields if provided
        if product_data.name is not None:
            product.name = product_data.name
        if product_data.description is not None:
            product.description = product_data.description
        if product_data.price is not None:
            product.price = product_data.price
        if product_data.sku is not None:
            product.sku = product_data.sku
        if product_data.stock_quantity is not None:
            product.stock_quantity = product_data.stock_quantity
        
        product.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return self._to_domain_model(product)

    async def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """
        Update product stock quantity.
        
        Args:
            product_id: The unique product ID
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated Product object if found, None otherwise
        """
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return None
        
        product.stock_quantity += quantity_change
        if product.stock_quantity < 0:
            product.stock_quantity = 0
        
        product.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return self._to_domain_model(product)

    async def delete_product(self, product_id: int) -> bool:
        """
        Delete a product by its ID.
        
        Args:
            product_id: The unique product ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        result = await self.db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return False
        
        await self.db.delete(product)
        await self.db.commit()
        return True

    def _to_domain_model(self, product_model: ProductModel) -> Product:
        """
        Convert SQLAlchemy model to domain model.
        
        Args:
            product_model: SQLAlchemy ProductModel object
            
        Returns:
            Domain Product object
        """
        return Product(
            id=product_model.id,
            name=product_model.name,
            description=product_model.description,
            price=product_model.price,
            sku=product_model.sku,
            stock_quantity=product_model.stock_quantity,
            created_at=product_model.created_at,
            updated_at=product_model.updated_at,
        )
