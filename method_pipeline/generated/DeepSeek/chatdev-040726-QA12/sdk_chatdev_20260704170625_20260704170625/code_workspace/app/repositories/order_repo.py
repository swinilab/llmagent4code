"""Order repository with domain-specific queries."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import OrderStatus
from app.entities import LineItemEntity, OrderEntity
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[OrderEntity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderEntity)

    async def get_with_items(self, id_: str) -> OrderEntity | None:
        stmt = (
            select(OrderEntity)
            .options(selectinload(OrderEntity.line_items))
            .where(OrderEntity.id == id_)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[OrderEntity]:
        """List all orders with eagerly loaded line items (avoids async lazy-load)."""
        stmt = (
            select(OrderEntity)
            .options(selectinload(OrderEntity.line_items))
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: OrderStatus) -> list[OrderEntity]:
        stmt = (
            select(OrderEntity)
            .where(OrderEntity.status == status)
            .options(selectinload(OrderEntity.line_items))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, id_: str, new_status: OrderStatus) -> OrderEntity | None:
        entity = await self.get(id_)
        if entity is None:
            return None
        entity.status = new_status
        await self._session.flush()
        return entity

    async def save_line_items(
        self, order_id: str, items: list[dict]
    ) -> list[LineItemEntity]:
        entities = []
        for item in items:
            li = LineItemEntity(
                order_id=order_id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
            )
            self._session.add(li)
            entities.append(li)
        await self._session.flush()
        return entities