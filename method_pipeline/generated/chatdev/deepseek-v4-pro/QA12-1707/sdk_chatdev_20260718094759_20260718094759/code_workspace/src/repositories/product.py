"""Product repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Data access for Product entities."""

    model = Product

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def search_by_description(self, fragment: str, limit: int = 50) -> list[Product]:
        """Search products by description substring."""
        stmt = (
            select(Product)
            .where(Product.description.ilike(f"%{fragment}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
