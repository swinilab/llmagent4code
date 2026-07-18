"""Invoice repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.invoice import Invoice
from src.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Data access for Invoice entities."""

    model = Invoice

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_order_id(self, order_id: str) -> Invoice | None:
        """Fetch invoice by its order ID."""
        stmt = select(Invoice).where(Invoice.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
