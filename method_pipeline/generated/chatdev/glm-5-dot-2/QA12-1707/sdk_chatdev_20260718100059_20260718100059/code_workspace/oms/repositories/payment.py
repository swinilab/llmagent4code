"""
Payment repository — data access for Payment entities.
"""
from typing import Sequence

from sqlalchemy import select

from oms.enums import PaymentStatus
from oms.models.payment import Payment
from oms.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment CRUD + verification queries."""

    model = Payment

    async def get_by_order(self, order_id: str) -> Sequence[Payment]:
        """Fetch all payments for an order."""
        stmt = select(Payment).where(Payment.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_verified_by_order(self, order_id: str) -> Payment | None:
        """Fetch the first verified payment for an order, if any."""
        stmt = select(Payment).where(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.VERIFIED,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()