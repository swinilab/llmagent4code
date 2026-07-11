"""
Order repository with line-item loading.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Order, OrderLineItem
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Order)

    async def get_with_items(self, order_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.line_items))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_items_or_fail(self, order_id: int) -> Order:
        from app.domain.exceptions import EntityNotFound
        order = await self.get_with_items(order_id)
        if order is None:
            raise EntityNotFound("Order", order_id)
        return order

    async def list_by_customer(
        self, customer_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        from sqlalchemy import func
        offset = (page - 1) * page_size
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .options(selectinload(Order.line_items))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        count_stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.customer_id == customer_id)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()
        return items, total
