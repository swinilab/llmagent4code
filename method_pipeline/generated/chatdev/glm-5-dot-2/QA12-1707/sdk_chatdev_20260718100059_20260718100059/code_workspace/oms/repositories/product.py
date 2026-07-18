"""
Product repository — data access for Product entities.
"""
from typing import Any, Sequence

from sqlalchemy import func, or_, select

from oms.models.product import Product
from oms.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for Product CRUD + search."""

    model = Product

    async def search(
        self,
        query: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        currency: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Product], int]:
        """
        Search products by description keyword and/or price range.

        Returns (items, total_count).
        """
        stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(Product.description.ilike(pattern))
            count_stmt = count_stmt.where(Product.description.ilike(pattern))

        if min_price is not None:
            stmt = stmt.where(Product.base_price >= min_price)
            count_stmt = count_stmt.where(Product.base_price >= min_price)

        if max_price is not None:
            stmt = stmt.where(Product.base_price <= max_price)
            count_stmt = count_stmt.where(Product.base_price <= max_price)

        if currency is not None:
            stmt = stmt.where(Product.currency == currency)
            count_stmt = count_stmt.where(Product.currency == currency)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total