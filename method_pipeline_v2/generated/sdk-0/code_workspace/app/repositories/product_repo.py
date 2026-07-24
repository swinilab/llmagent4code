"""
Product repository with search support.
"""
from __future__ import annotations

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Product)

    async def search(
        self,
        query: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        stmt = select(Product)
        count_stmt = select(func.count(Product.id))

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(Product.name.ilike(pattern), Product.description.ilike(pattern))
            )
            count_stmt = count_stmt.where(
                or_(Product.name.ilike(pattern), Product.description.ilike(pattern))
            )

        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        products = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return products, total
