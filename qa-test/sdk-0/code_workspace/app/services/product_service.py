"""ProductService – business logic for product retrieval.

Implements caching to satisfy **NFR 1.1 Response Time**.
"""

import asyncio
from typing import List
from app.db.models import Product
from app.api.v1.dtos.product_dto import ProductResponseDTO
from app.cache.response_cache import ResponseCache

class ProductService:
    def __init__(self):
        self._cache = ResponseCache()

    async def get_all_products(self) -> List[ProductResponseDTO]:
        # Direct DB fetch (no cache) – used when system is not degraded.
        async with Product.async_session() as session:
            result = await session.execute(Product.select())
            products = result.scalars().all()
        dtos = [ProductResponseDTO.from_orm(p) for p in products]
        # Populate cache for future calls
        await self._cache.set("product_list", dtos)
        return dtos

    async def get_cached_products(self) -> List[ProductResponseDTO]:
        # Try cache first; fallback to DB if miss (still fast enough for degraded mode).
        cached = await self._cache.get("product_list")
        if cached is not None:
            return cached
        return await self.get_all_products()
