"""
Product service — search/browse (hot path for NFR 1.1, p95 ≤ 150 ms)
with Redis caching.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product
from app.domain.schemas import ProductCreate, ProductSearchParams
from app.infrastructure.cache import (
    cache_product,
    cache_search_result,
    get_cached_product,
    get_cached_search_result,
    invalidate_product_cache,
)
from app.repositories.product import ProductRepository


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductRepository(session)

    async def create_product(self, data: ProductCreate) -> Product:
        product = Product(
            description=data.description,
            base_price=data.base_price,
            currency=data.currency,
            stock_available=data.stock_available,
        )
        created = await self._repo.add(product)
        await cache_product(created.id, self._to_dict(created))
        return created

    async def get_product(self, product_id: int) -> Product:
        # Try cache first — short-circuit DB on hit
        cached = await get_cached_product(product_id)
        if cached is not None:
            # Reconstruct a Product from cached data so the controller's
            # Pydantic response model can validate it via from_attributes.
            product = Product(
                id=cached["id"],
                description=cached["description"],
                base_price=Decimal(cached["base_price"]),
                currency=cached["currency"],
                stock_available=cached["stock_available"],
            )
            if cached.get("created_at"):
                product.created_at = datetime.fromisoformat(cached["created_at"])
            if cached.get("updated_at"):
                product.updated_at = datetime.fromisoformat(cached["updated_at"])
            return product

        # Cache miss — load from DB and warm cache
        product = await self._repo.get_or_fail(product_id)
        await cache_product(product.id, self._to_dict(product))
        return product

    async def search_products(self, params: ProductSearchParams) -> tuple[list[Product], int]:
        # Try cached search result — stores a dict with product IDs and total count
        cache_key_query = params.q or ""
        cached = await get_cached_search_result(
            cache_key_query, params.page, params.page_size
        )
        if cached is not None:
            # Reconstruct products from individual product caches
            product_ids: list[int] = cached.get("product_ids", [])
            total: int = cached.get("total", 0)
            products: list[Product] = []
            for pid in product_ids:
                pdata = await get_cached_product(pid)
                if pdata is not None:
                    product = Product(
                        id=pdata["id"],
                        description=pdata["description"],
                        base_price=Decimal(pdata["base_price"]),
                        currency=pdata["currency"],
                        stock_available=pdata["stock_available"],
                    )
                    if pdata.get("created_at"):
                        product.created_at = datetime.fromisoformat(pdata["created_at"])
                    if pdata.get("updated_at"):
                        product.updated_at = datetime.fromisoformat(pdata["updated_at"])
                    products.append(product)
            if products:
                return products, total

        items, total = await self._repo.search(
            query=params.q,
            min_price=params.min_price,
            max_price=params.max_price,
            in_stock_only=params.in_stock_only,
            page=params.page,
            page_size=params.page_size,
        )

        # Cache individual products and the search result metadata
        product_ids = []
        for p in items:
            await cache_product(p.id, self._to_dict(p))
            product_ids.append(p.id)

        await cache_search_result(
            cache_key_query,
            params.page,
            params.page_size,
            {"product_ids": product_ids, "total": total},
        )

        return items, total

    async def update_product(
        self, product_id: int, data: ProductCreate
    ) -> Product:
        product = await self._repo.get_or_fail(product_id)
        product.description = data.description
        product.base_price = data.base_price
        product.currency = data.currency
        product.stock_available = data.stock_available
        self._session.add(product)
        await self._session.flush()
        await invalidate_product_cache(product_id)
        await cache_product(product_id, self._to_dict(product))
        return product

    @staticmethod
    def _to_dict(product: Product) -> dict:
        return {
            "id": product.id,
            "description": product.description,
            "base_price": str(product.base_price),
            "currency": product.currency,
            "stock_available": product.stock_available,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        }
