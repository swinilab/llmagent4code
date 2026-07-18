"""Order repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import Order, OrderStatus
from src.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Data access for Order entities."""

    model = Order

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_customer(self, customer_id: str, limit: int = 100) -> list[Order]:
        """List orders for a specific customer."""
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: OrderStatus, limit: int = 100) -> list[Order]:
        """List orders filtered by status."""
        stmt = (
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending(self, limit: int = 100) -> list[Order]:
        """Shortcut for pending orders (used by staff review queue)."""
        return await self.list_by_status(OrderStatus.PENDING, limit=limit)
