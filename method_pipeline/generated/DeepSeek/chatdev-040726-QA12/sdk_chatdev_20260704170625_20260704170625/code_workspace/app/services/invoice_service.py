"""Invoice service — handles invoice creation and lifecycle."""

from __future__ import annotations

from datetime import timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Invoice, InvoiceStatus, utcnow
from app.entities import InvoiceEntity
from app.repositories.invoice_repo import InvoiceRepository


class InvoiceService:
    """Manages invoice creation, issuing, and status transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = InvoiceRepository(session)

    async def create_invoice(
        self,
        order_id: str,
        customer_id: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        due_days: int = 30,
    ) -> Invoice:
        import uuid
        now = utcnow()
        entity = InvoiceEntity(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            billing_name=billing_name,
            billing_address=billing_address,
            total_amount=total_amount,
            issue_date=now,
            due_date=now + timedelta(days=due_days),
            status=InvoiceStatus.ISSUED.value,
        )
        saved = await self._repo.save(entity)
        return Invoice.model_validate(saved)

    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        entity = await self._repo.get(invoice_id)
        return Invoice.model_validate(entity) if entity else None

    async def list_invoices(self) -> list[Invoice]:
        entities = await self._repo.list_all()
        return [Invoice.model_validate(e) for e in entities]

    async def get_by_order(self, order_id: str) -> list[Invoice]:
        entities = await self._repo.get_by_order(order_id)
        return [Invoice.model_validate(e) for e in entities]

    async def mark_paid(self, invoice_id: str) -> Optional[Invoice]:
        entity = await self._repo.get(invoice_id)
        if entity is None or entity.status not in (InvoiceStatus.ISSUED.value, InvoiceStatus.OVERDUE.value):
            return None
        entity.status = InvoiceStatus.PAID.value
        await self._repo.flush()
        return Invoice.model_validate(entity)