"""
OMS Product Service - Business logic for product management.
"""
from typing import List, Optional
import uuid
from decimal import Decimal
from app.domain.entities.models import Product, Money, Currency
from app.domain.repositories.interfaces import ProductRepository


class ProductService:
    """Service for product operations."""

    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    def create_product(
        self,
        sku: str,
        name: str,
        price_amount: str,
        description: Optional[str] = None,
        stock_quantity: int = 0,
        category: Optional[str] = None
    ) -> Product:
        """Create a new product."""
        existing = self._repo.find_by_sku(sku)
        if existing:
            raise ValueError(f"Product with SKU {sku} already exists")
        
        product = Product(
            id=str(uuid.uuid4()),
            sku=sku,
            name=name,
            description=description,
            price=Money(amount=Decimal(price_amount), currency=Currency.USD),
            stock_quantity=stock_quantity,
            category=category
        )
        return self._repo.save(product)

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self._repo.find_by_id(product_id)

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        return self._repo.find_by_sku(sku)

    def search_products(self, query: str) -> List[Product]:
        """Search products by name or description."""
        return self._repo.search(query)

    def list_products_by_category(self, category: str) -> List[Product]:
        """List products by category."""
        return self._repo.find_by_category(category)

    def list_active_products(self) -> List[Product]:
        """List all active products."""
        return self._repo.find_active()

    def update_stock(self, product_id: str, quantity: int) -> Optional[Product]:
        """Update product stock quantity."""
        return self._repo.update(product_id, {'stock_quantity': quantity})

    def reserve_stock(self, product_id: str, quantity: int) -> bool:
        """Reserve stock for an order."""
        product = self._repo.find_by_id(product_id)
        if not product or product.stock_quantity < quantity:
            return False
        self._repo.update(product_id, {'stock_quantity': product.stock_quantity - quantity})
        return True

    def release_stock(self, product_id: str, quantity: int) -> bool:
        """Release reserved stock."""
        product = self._repo.find_by_id(product_id)
        if not product:
            return False
        self._repo.update(product_id, {'stock_quantity': product.stock_quantity + quantity})
        return True
