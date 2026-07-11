"""Invoice repository with eager-loaded relationships to prevent async lazy-load crashes."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.entities import InvoiceEntity
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[InvoiceEntity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvoiceEntity)

    async def get(self, id_: str) -> InvoiceEntity | None:
        """Get invoice with eagerly loaded customer relationship (NFR 1.2)."""
        stmt = (
            select(InvoiceEntity)
            .options(selectinload(InvoiceEntity.customer))
            .where(InvoiceEntity.id == id_)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[InvoiceEntity]:
        """List all invoices with eagerly loaded customer relationship."""
        stmt = (
            select(InvoiceEntity)
            .options(selectinload(InvoiceEntity.customer))
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_order(self, order_id: str) -> list[InvoiceEntity]:
        """Get invoices by order with eagerly loaded customer relationship.

        Uses selectinload to prevent MissingGreenlet errors in async context
        if the Invoice domain model is extended with a customer field (NFR 1.2).
        """
        stmt = (
            select(InvoiceEntity)
            .options(selectinload(InvoiceEntity.customer))
            .where(InvoiceEntity.order_id == order_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())