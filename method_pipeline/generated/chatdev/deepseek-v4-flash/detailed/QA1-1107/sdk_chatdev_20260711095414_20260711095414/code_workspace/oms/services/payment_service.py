"""
Payment service — idempotent payment processing.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.enums import PaymentMethod, PaymentStatus
from oms.domain.models import Payment
from oms.infrastructure.entities import PaymentModel
from oms.repositories.payment_repo import PaymentRepository


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PaymentRepository(session)

    async def get_payment(self, payment_id: UUID) -> Optional[PaymentModel]:
        return await self._repo.get(payment_id)

    async def get_payments_by_order(self, order_id: UUID) -> list[PaymentModel]:
        return await self._repo.get_by_order(order_id)
