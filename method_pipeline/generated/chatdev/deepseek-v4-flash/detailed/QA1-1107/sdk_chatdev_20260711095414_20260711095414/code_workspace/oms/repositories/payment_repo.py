"""
Payment repository.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.infrastructure.entities import PaymentModel
from oms.repositories import BaseRepository


class PaymentRepository(BaseRepository[PaymentModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentModel)

    async def get_by_order(self, order_id: UUID) -> list[PaymentModel]:
        stmt = select(PaymentModel).where(PaymentModel.order_id == order_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_idempotency_key(self, key: str) -> Optional[PaymentModel]:
        stmt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
