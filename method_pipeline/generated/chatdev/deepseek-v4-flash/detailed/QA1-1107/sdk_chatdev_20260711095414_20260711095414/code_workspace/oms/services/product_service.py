"""
Product service — handles browse/search with cache-aside.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.models import Product as ProductDomain
from oms.infrastructure.entities import ProductModel
from oms.repositories.product_repo import ProductRepository


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductRepository(session)

    async def get_product(self, product_id: UUID) -> Optional[ProductDomain]:
        """Cache-aside read. Returns domain Product (Pydantic), not ORM model."""
        return await self._repo.get_with_cache(product_id)

    async def search_products(self, query: str, limit: int = 20) -> list[ProductDomain]:
        """Search with cache-aside for result IDs (TTL=30s)."""
        return await self._repo.search_with_cache(query, limit)

    async def list_products(self, skip: int = 0, limit: int = 50) -> list[ProductModel]:
        stmt = select(ProductModel).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_price(self, product_id: UUID, new_price: float) -> Optional[ProductModel]:
        return await self._repo.update_price(product_id, new_price)

    async def update_stock(self, product_id: UUID, delta: int) -> Optional[ProductModel]:
        return await self._repo.update_stock(product_id, delta)
