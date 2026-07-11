"""
Order repository with optimistic-lock support.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.enums import OrderStatus
from oms.infrastructure.entities import OrderModel
from oms.repositories import BaseRepository


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderModel)

    async def get_by_customer(self, customer_id: UUID) -> list[OrderModel]:
        stmt = select(OrderModel).where(OrderModel.customer_id == customer_id).order_by(OrderModel.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        order_id: UUID,
        new_status: OrderStatus,
        expected_version: int,
        timestamp_field: str | None = None,
    ) -> Optional[OrderModel]:
        """
        Optimistic-lock update of order status.
        Accepts an OrderStatus enum value (not a string) for type safety.
        Returns updated model or None if version conflict.
        """
        now = _utcnow()
        values = {
            "status": new_status,
            "version": OrderModel.version + 1,
            "updated_at": now,
        }
        if timestamp_field:
            values[timestamp_field] = now

        stmt = (
            update(OrderModel)
            .where(OrderModel.id == order_id, OrderModel.version == expected_version)
            .values(**values)
            .returning(OrderModel)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
