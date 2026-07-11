"""Payment repository."""

from typing import Optional

from sqlalchemy import select

from app.repositories.base import BaseRepository
from app.repositories.orm_models import PaymentModel


class PaymentRepository(BaseRepository[PaymentModel]):
    def __init__(self, session):
        super().__init__(PaymentModel, session)

    async def get_by_idempotency_key(self, key: str) -> Optional[PaymentModel]:
        """Find a payment by its idempotency key."""
        stmt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id) -> Optional[PaymentModel]:
        """Get the most recent payment for an order."""
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_payments_by_order(self, order_id) -> list[PaymentModel]:
        """Get all payments for an order."""
        stmt = select(PaymentModel).where(PaymentModel.order_id == order_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
