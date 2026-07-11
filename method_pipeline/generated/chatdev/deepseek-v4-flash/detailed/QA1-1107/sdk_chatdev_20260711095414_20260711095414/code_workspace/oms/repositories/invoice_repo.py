"""
Invoice repository.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.infrastructure.entities import InvoiceModel
from oms.repositories import BaseRepository


class InvoiceRepository(BaseRepository[InvoiceModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvoiceModel)

    async def get_by_order(self, order_id: UUID) -> list[InvoiceModel]:
        stmt = select(InvoiceModel).where(InvoiceModel.order_id == order_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
