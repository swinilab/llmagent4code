"""
Product repository with cache-aside integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.models import Product as ProductDomain
from oms.infrastructure.cache import (
    get_cached_product,
    set_cached_product,
    invalidate_product_cache,
    get_cached_search_results,
    set_cached_search_results,
)
from oms.infrastructure.entities import ProductModel
from oms.repositories import BaseRepository


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _model_to_domain(m: ProductModel) -> ProductDomain:
    """Convert ORM ProductModel to domain Product (Pydantic)."""
    return ProductDomain(
        id=m.id,
        description=m.description,
        base_price=m.base_price,
        currency=m.currency,
        stock_available=m.stock_available,
        last_modified=m.last_modified,
    )


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductModel)

    async def get_with_cache(self, product_id: UUID) -> Optional[ProductDomain]:
        """Cache-aside: check Redis first, fall back to DB, populate cache.
        Returns a domain Product (Pydantic), NOT an ORM model, to avoid
        type errors when reconstructing from cached string-typed dict.
        """
        cached = await get_cached_product(product_id)
        if cached:
            # Reconstruct the Pydantic domain model from cached dict
            return ProductDomain(
                id=UUID(cached["id"]),
                description=cached["description"],
                base_price=Decimal(cached["base_price"]),
                currency=cached["currency"],
                stock_available=cached["stock_available"],
                last_modified=datetime.fromisoformat(cached["last_modified"]),
            )
        product = await self.get(product_id)
        if product:
            await set_cached_product(product_id, {
                "id": str(product.id),
                "description": product.description,
                "base_price": str(product.base_price),
                "currency": product.currency,
                "stock_available": product.stock_available,
                "last_modified": product.last_modified.isoformat(),
            })
            return _model_to_domain(product)
        return None

    async def search_with_cache(self, query: str, limit: int = 20) -> list[ProductDomain]:
        """Cache search result IDs (TTL=30s), then fetch each product via cache-aside."""
        cache_key = f"search:{query}:{limit}"
        cached_ids = await get_cached_search_results(cache_key)
        if cached_ids:
            products = []
            for pid_str in cached_ids:
                p = await self.get_with_cache(UUID(pid_str))
                if p:
                    products.append(p)
            return products

        # Fall back to DB
        stmt = (
            select(ProductModel)
            .where(ProductModel.description.ilike(f"%{query}%"))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = list(result.scalars().all())
        domains = [_model_to_domain(m) for m in models]

        # Cache the result IDs with a shorter TTL (30s)
        await set_cached_search_results(
            cache_key, [str(d.id) for d in domains], ttl=30
        )

        # Also warm individual product caches
        for d in domains:
            await set_cached_product(d.id, {
                "id": str(d.id),
                "description": d.description,
                "base_price": str(d.base_price),
                "currency": d.currency,
                "stock_available": d.stock_available,
                "last_modified": d.last_modified.isoformat(),
            })

        return domains

    async def update_price(self, product_id: UUID, new_price: float) -> Optional[ProductModel]:
        """Update price and invalidate cache."""
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .values(base_price=new_price, last_modified=_utcnow())
            .returning(ProductModel)
        )
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()
        if product:
            await invalidate_product_cache(product_id)
        return product

    async def update_stock(self, product_id: UUID, delta: int) -> Optional[ProductModel]:
        """Adjust stock and invalidate cache."""
        product = await self.get(product_id)
        if not product:
            return None
        new_stock = max(0, product.stock_available + delta)
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .values(stock_available=new_stock, last_modified=_utcnow())
            .returning(ProductModel)
        )
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()
        if product:
            await invalidate_product_cache(product_id)
        return product

    async def atomic_decrement_stock(self, product_id: UUID, quantity: int) -> bool:
        """Atomically decrement stock if sufficient. Returns True if successful."""
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id, ProductModel.stock_available >= quantity)
            .values(
                stock_available=ProductModel.stock_available - quantity,
                last_modified=_utcnow(),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
