"""
Payment repository.
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Payment
from app.models.enums import PaymentStatus
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Payment)

    async def get_by_order(self, order_id: str) -> Payment | None:
        stmt = select(Payment).where(Payment.order_id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: PaymentStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Payment], int]:
        stmt = select(Payment)
        count_stmt = select(func.count(Payment.id))

        if status:
            stmt = stmt.where(Payment.status == status)
            count_stmt = count_stmt.where(Payment.status == status)

        stmt = stmt.offset(skip).limit(limit).order_by(Payment.timestamp.desc())
        result = await self._session.execute(stmt)
        payments = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return payments, total
