"""Payment service — handles payment processing and verification."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Payment, PaymentMethod, PaymentStatus
from app.entities import PaymentEntity
from app.repositories.payment_repo import PaymentRepository


class PaymentService:
    """Manages payment records and status transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PaymentRepository(session)

    async def create_payment(
        self,
        order_id: str,
        invoice_id: str,
        amount: Decimal,
        method: PaymentMethod,
    ) -> Payment:
        import uuid
        entity = PaymentEntity(
            id=str(uuid.uuid4()),
            order_id=order_id,
            invoice_id=invoice_id,
            amount=amount,
            method=method.value,
            status=PaymentStatus.PENDING.value,
        )
        saved = await self._repo.save(entity)
        return Payment.model_validate(saved)

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        entity = await self._repo.get(payment_id)
        return Payment.model_validate(entity) if entity else None

    async def list_payments(self) -> list[Payment]:
        entities = await self._repo.list_all()
        return [Payment.model_validate(e) for e in entities]

    async def get_by_order(self, order_id: str) -> list[Payment]:
        entities = await self._repo.get_by_order(order_id)
        return [Payment.model_validate(e) for e in entities]

    async def get_by_invoice(self, invoice_id: str) -> list[Payment]:
        entities = await self._repo.get_by_invoice(invoice_id)
        return [Payment.model_validate(e) for e in entities]

    async def complete_payment(self, payment_id: str) -> Optional[Payment]:
        entity = await self._repo.get(payment_id)
        if entity is None or entity.status != PaymentStatus.PENDING.value:
            return None
        entity.status = PaymentStatus.COMPLETED.value
        await self._repo.flush()
        return Payment.model_validate(entity)