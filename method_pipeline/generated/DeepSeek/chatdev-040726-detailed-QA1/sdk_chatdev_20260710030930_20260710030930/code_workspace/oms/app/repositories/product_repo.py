"""Product repository with cache-aware read methods and atomic stock operations."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update

from app.domain.enums import Currency
from app.infrastructure.cache import (
    get_cached_product,
    get_cached_search,
    invalidate_product_cache,
    invalidate_search_cache,
    set_cached_product,
    set_cached_search,
)
from app.repositories.base import BaseRepository
from app.repositories.orm_models import ProductModel


def _cached_dict_to_product_model(data: dict[str, Any]) -> ProductModel:
    """Convert a cached dict (with string values) back to a ProductModel.

    Redis stores everything as strings, so we need explicit type coercion
    to match the SQLAlchemy ORM model's expected types.
    """
    return ProductModel(
        id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        name=data["name"],
        description=data["description"],
        base_price=Decimal(str(data["base_price"])),
        currency=Currency(data["currency"]) if isinstance(data["currency"], str) else data["currency"],
        stock_available=int(data["stock_available"]),
        last_modified=(
            datetime.fromisoformat(data["last_modified"])
            if data.get("last_modified")
            else None
        ),
        created_at=(
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        ),
    )


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, session):
        super().__init__(ProductModel, session)

    async def get_by_id_cached(self, product_id: UUID) -> Optional[ProductModel]:
        """Get product by ID with cache-aside (Redis)."""
        # Try cache first
        cached = await get_cached_product(str(product_id))
        if cached is not None:
            # Reconstruct model from cached dict with proper type coercion
            return _cached_dict_to_product_model(cached)

        # Cache miss: load from DB
        product = await self.get_by_id(product_id)
        if product is not None:
            # Populate cache
            await set_cached_product(
                str(product_id),
                {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "base_price": str(product.base_price),
                    "currency": product.currency.value if hasattr(product.currency, "value") else product.currency,
                    "stock_available": product.stock_available,
                    "last_modified": product.last_modified.isoformat() if product.last_modified else None,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                },
            )
        return product

    async def search_cached(self, query: str, page: int = 1, page_size: int = 20) -> list[ProductModel]:
        """Search products with cache-aside."""
        # Try cache first
        cached = await get_cached_search(query, page, page_size)
        if cached is not None:
            return [_cached_dict_to_product_model(item) for item in cached]

        # Cache miss: search DB
        stmt = (
            select(ProductModel)
            .where(ProductModel.name.ilike(f"%{query}%"))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        products = list(result.scalars().all())

        # Populate cache
        product_dicts = [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "base_price": str(p.base_price),
                "currency": p.currency.value if hasattr(p.currency, "value") else p.currency,
                "stock_available": p.stock_available,
                "last_modified": p.last_modified.isoformat() if p.last_modified else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ]
        await set_cached_search(query, page, page_size, product_dicts)
        return products

    async def decrement_stock(self, product_id: UUID, quantity: int) -> Optional[ProductModel]:
        """Atomically decrement stock if sufficient quantity available.

        Uses a SQL WHERE guard to prevent overselling under concurrent load.
        The UPDATE only succeeds if stock_available >= quantity, making this
        an atomic compare-and-swap at the database level.

        Args:
            product_id: The product UUID.
            quantity: The quantity to decrement (must be > 0).

        Returns:
            The updated ProductModel if the decrement succeeded,
            None if stock was insufficient (no rows updated).
        """
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .where(ProductModel.stock_available >= quantity)  # Guard: only decrement if enough stock
            .values(stock_available=ProductModel.stock_available - quantity)
            .returning(ProductModel)
        )
        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is not None:
            await self.session.flush()
        return updated

    async def increment_stock(self, product_id: UUID, quantity: int) -> Optional[ProductModel]:
        """Atomically increment stock (used on order cancellation).

        Args:
            product_id: The product UUID.
            quantity: The quantity to add back (must be > 0).

        Returns:
            The updated ProductModel.
        """
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .values(stock_available=ProductModel.stock_available + quantity)
            .returning(ProductModel)
        )
        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is not None:
            await self.session.flush()
        return updated

    async def update_price_or_stock(self, product_id: UUID, data: dict) -> Optional[ProductModel]:
        """Update product price/stock and invalidate cache."""
        result = await self.update(product_id, data)
        if result is not None:
            # Invalidate caches
            await invalidate_product_cache(str(product_id))
            await invalidate_search_cache()
        return result
