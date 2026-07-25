"""
Order repository with status filtering.
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Order, OrderItem
from app.models.enums import OrderStatus
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Order)

    async def get_with_items(self, id: str) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.line_items).selectinload(OrderItem.product),
                selectinload(Order.customer),
                selectinload(Order.payment),
                selectinload(Order.invoice),
            )
            .where(Order.id == id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: OrderStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Order], int]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.line_items).selectinload(OrderItem.product),
                selectinload(Order.customer),
                selectinload(Order.payment),
                selectinload(Order.invoice),
            )
        )
        count_stmt = select(func.count(Order.id))

        if status:
            stmt = stmt.where(Order.status == status)
            count_stmt = count_stmt.where(Order.status == status)

        stmt = stmt.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await self._session.execute(stmt)
        orders = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return orders, total

    async def list_pending_processing(self) -> list[Order]:
        """Return orders that need processing after a crash (non-terminal states)."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.line_items).selectinload(OrderItem.product),
                selectinload(Order.customer),
                selectinload(Order.payment),
                selectinload(Order.invoice),
            )
            .where(
                Order.status.in_([
                    OrderStatus.PENDING,
                    OrderStatus.REVIEWED,
                    OrderStatus.ACCEPTED,
                    OrderStatus.INVOICED,
                    OrderStatus.PAID,
                ])
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
