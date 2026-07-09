"""
Base repository with common CRUD operations.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository providing common data-access methods."""

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self._session = session
        self._model = model_cls

    async def get(self, entity_id: int) -> Optional[T]:
        return await self._session.get(self._model, entity_id)

    async def get_or_fail(self, entity_id: int) -> T:
        from app.domain.exceptions import EntityNotFound
        entity = await self.get(entity_id)
        if entity is None:
            raise EntityNotFound(self._model.__name__, entity_id)
        return entity

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Any | None = None,
        filters: list | None = None,
    ) -> tuple[list[T], int]:
        query = select(self._model)
        if filters:
            query = query.where(*filters)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.offset(offset).limit(limit)

        count_query = select(func.count()).select_from(self._model)
        if filters:
            count_query = count_query.where(*filters)

        result = await self._session.execute(query)
        items = list(result.scalars().all())

        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()

        return items, total

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete(self, entity_id: int) -> None:
        entity = await self.get_or_fail(entity_id)
        await self._session.delete(entity)
        await self._session.flush()
