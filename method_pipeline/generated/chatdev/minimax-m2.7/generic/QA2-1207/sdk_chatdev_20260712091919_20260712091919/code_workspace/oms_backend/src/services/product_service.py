"""
Product Service - business logic for product catalog management.
"""
import logging
from typing import List, Optional

from ..domain.models import Product
from ..infrastructure.repositories import ProductRepository
from ..infrastructure.database import SessionLocal

logger = logging.getLogger(__name__)


class ProductService:
    """Service layer for product operations."""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self._repo = None

    @property
    def repo(self) -> ProductRepository:
        if self._repo is None:
            if self.db_session:
                self._repo = ProductRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._repo

    def create_product(self, sku: str, description: str, base_price: float,
                      currency: str = "USD", stock_quantity: int = 0) -> Product:
        """Create a new product."""
        product = Product(
            sku=sku,
            description=description,
            base_price=base_price,
            currency=currency,
            stock_quantity=stock_quantity,
            is_active=True
        )
        return self.repo.create(product)

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self.repo.get_by_id(product_id)

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        return self.repo.get_by_sku(sku)

    def update_product(self, product_id: str, **kwargs) -> Optional[Product]:
        """Update product fields."""
        product = self.repo.get_by_id(product_id)
        if not product:
            return None

        for key, value in kwargs.items():
            if hasattr(product, key) and value is not None:
                setattr(product, key, value)

        return self.repo.update(product)

    def deactivate_product(self, product_id: str) -> Optional[Product]:
        """Deactivate a product (soft delete)."""
        return self.update_product(product_id, is_active=False)

    def activate_product(self, product_id: str) -> Optional[Product]:
        """Activate a product."""
        return self.update_product(product_id, is_active=True)

    def list_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """List all products."""
        return self.repo.get_all(skip=skip, limit=limit)

    def list_active_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """List active products only."""
        return self.repo.get_active_products(skip=skip, limit=limit)

    def update_stock(self, product_id: str, quantity_change: int) -> Optional[Product]:
        """Update stock quantity (positive to add, negative to remove)."""
        product = self.repo.get_by_id(product_id)
        if not product:
            return None

        new_quantity = product.stock_quantity + quantity_change
        if new_quantity < 0:
            raise ValueError(f"Insufficient stock. Current: {product.stock_quantity}, requested change: {quantity_change}")

        return self.update_product(product_id, stock_quantity=new_quantity)


def get_product_service(db_session=None) -> ProductService:
    """Factory function to get product service."""
    return ProductService(db_session)
