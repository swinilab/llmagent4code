"""
Invoice repository.
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Invoice
from app.models.enums import InvoiceStatus
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Invoice)

    async def get_by_order(self, order_id: str) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.order_id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: InvoiceStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Invoice], int]:
        stmt = select(Invoice)
        count_stmt = select(func.count(Invoice.id))

        if status:
            stmt = stmt.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        stmt = stmt.offset(skip).limit(limit).order_by(Invoice.created_at.desc())
        result = await self._session.execute(stmt)
        invoices = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return invoices, total
