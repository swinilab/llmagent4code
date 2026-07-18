"""Customer repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.customer import Customer
from src.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Data access for Customer entities."""

    model = Customer

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_phone(self, phone: str) -> Customer | None:
        """Find customer by phone number."""
        stmt = select(Customer).where(Customer.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_name(self, name_fragment: str, limit: int = 50) -> list[Customer]:
        """Full-text-like search on customer name."""
        stmt = (
            select(Customer)
            .where(Customer.name.ilike(f"%{name_fragment}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
