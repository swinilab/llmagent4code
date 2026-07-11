"""Payment repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities import PaymentEntity
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[PaymentEntity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentEntity)

    async def get_by_order(self, order_id: str) -> list[PaymentEntity]:
        stmt = select(PaymentEntity).where(PaymentEntity.order_id == order_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_invoice(self, invoice_id: str) -> list[PaymentEntity]:
        stmt = select(PaymentEntity).where(PaymentEntity.invoice_id == invoice_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())