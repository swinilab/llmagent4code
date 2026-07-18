"""
Customer repository — data access for Customer entities.
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from oms.models.customer import Customer
from oms.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer CRUD + custom queries."""

    model = Customer

    async def get_with_orders(self, id: str) -> Customer | None:
        """Fetch customer with eagerly loaded order history."""
        stmt = (
            select(Customer)
            .where(Customer.id == id)
            .options(selectinload(Customer.orders))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Customer | None:
        """Find a customer by exact name match."""
        stmt = select(Customer).where(Customer.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()