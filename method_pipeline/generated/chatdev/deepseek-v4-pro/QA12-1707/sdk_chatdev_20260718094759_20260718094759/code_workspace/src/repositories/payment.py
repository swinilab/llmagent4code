"""Payment repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payment import Payment
from src.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Data access for Payment entities."""

    model = Payment

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_order(self, order_id: str) -> list[Payment]:
        """List all payments for an order."""
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
