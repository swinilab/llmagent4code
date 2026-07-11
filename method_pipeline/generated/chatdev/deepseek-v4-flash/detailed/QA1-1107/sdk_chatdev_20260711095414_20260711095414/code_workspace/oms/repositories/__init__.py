"""
Base repository with common CRUD operations.
"""
from __future__ import annotations

from typing import Generic, TypeVar, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from oms.infrastructure.entities import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self._session = session
        self._model = model_cls

    async def get(self, entity_id: UUID) -> Optional[T]:
        stmt = select(self._model).where(self._model.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()
