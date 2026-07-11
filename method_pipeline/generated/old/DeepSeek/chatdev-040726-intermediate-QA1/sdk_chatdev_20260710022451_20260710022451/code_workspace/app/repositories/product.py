"""
Product repository with search support.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Product)

    async def search(
        self,
        query: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        filters = []

        if query:
            like_pattern = f"%{query}%"
            filters.append(
                or_(
                    Product.description.ilike(like_pattern),
                )
            )
        if min_price is not None:
            filters.append(Product.base_price >= min_price)
        if max_price is not None:
            filters.append(Product.base_price <= max_price)
        if in_stock_only:
            filters.append(Product.stock_available > 0)

        offset = (page - 1) * page_size
        return await self.list(
            offset=offset,
            limit=page_size,
            order_by=Product.id,
            filters=filters,
        )
