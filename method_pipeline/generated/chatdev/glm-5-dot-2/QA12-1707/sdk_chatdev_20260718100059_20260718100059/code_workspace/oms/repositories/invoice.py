"""
Invoice repository — data access for Invoice entities.
"""
import datetime as dt
from typing import Sequence

from sqlalchemy import select

from oms.enums import InvoiceStatus
from oms.models.invoice import Invoice
from oms.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for Invoice CRUD + status queries."""

    model = Invoice

    async def get_by_order(self, order_id: str) -> Invoice | None:
        """Fetch the invoice for a given order (1:1 relationship)."""
        stmt = select(Invoice).where(Invoice.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_overdue(self) -> Sequence[Invoice]:
        """Fetch all issued invoices past their due date."""
        today = dt.date.today()
        stmt = select(Invoice).where(
            Invoice.status == InvoiceStatus.ISSUED,
            Invoice.due_date < today,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()