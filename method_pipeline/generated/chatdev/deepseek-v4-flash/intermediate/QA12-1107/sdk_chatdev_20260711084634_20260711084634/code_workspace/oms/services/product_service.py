"""
Product service: product catalog operations.

Product search/browse is on the latency-critical path (NFR 1.1, p95 ≤ 150ms).
Uses cache-aside for individual product lookups.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from oms.adapters.repositories import ProductRepository
from oms.domain.models import Money, Product
from oms.infrastructure.cache import cache_delete
from oms.infrastructure.database import get_session, get_readonly_session

logger = logging.getLogger(__name__)

_product_repo = ProductRepository()


class ProductService:
    """Business logic for product operations."""

    async def get_product(self, product_id: str) -> Product:
        """Get a product by ID (cache-aside, latency-critical)."""
        async with get_readonly_session() as session:
            return await _product_repo.get_by_id(session, product_id)

    async def list_available_products(self) -> list[Product]:
        """List all available products (browse path)."""
        async with get_readonly_session() as session:
            return await _product_repo.list_available(session)

    async def create_product(
        self,
        name: str,
        description: str,
        price_amount: Decimal,
        price_currency: str,
        stock: int,
    ) -> Product:
        """Create a new product."""
        async with get_session() as session:
            product = Product(
                name=name,
                description=description,
                base_price=Money(amount=price_amount, currency=price_currency),
                stock=stock,
                available=True,
            )
            await _product_repo.save(session, product)
            logger.info("Product %s created: %s", product.id, name)
            return product

    async def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price_amount: Optional[Decimal] = None,
        price_currency: Optional[str] = None,
        stock: Optional[int] = None,
        available: Optional[bool] = None,
    ) -> Product:
        """Update an existing product."""
        async with get_session() as session:
            product = await _product_repo.get_by_id(session, product_id)
            if name is not None:
                product.name = name
            if description is not None:
                product.description = description
            if price_amount is not None:
                product.base_price = Money(
                    amount=price_amount,
                    currency=price_currency or product.base_price.currency,
                )
            if stock is not None:
                product.stock = stock
            if available is not None:
                product.available = available
            await _product_repo.update(session, product)
            logger.info("Product %s updated", product_id)
            return product
