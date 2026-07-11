"""
Invoice service.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oms.infrastructure.entities import InvoiceModel
from oms.repositories.invoice_repo import InvoiceRepository


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InvoiceRepository(session)

    async def get_invoice(self, invoice_id: UUID) -> Optional[InvoiceModel]:
        return await self._repo.get(invoice_id)

    async def get_invoices_by_order(self, order_id: UUID) -> list[InvoiceModel]:
        return await self._repo.get_by_order(order_id)
