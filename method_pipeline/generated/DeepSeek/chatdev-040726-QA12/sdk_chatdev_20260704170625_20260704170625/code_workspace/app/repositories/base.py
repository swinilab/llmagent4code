"""Base repository with common CRUD operations (composition over inheritance)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Shared data-access behaviour extracted into a reusable mixin-compatible class."""

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self._session = session
        self._model = model_cls

    async def get(self, id_: str) -> T | None:
        stmt = select(self._model).where(self._model.id == id_)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[T]:
        stmt = select(self._model).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def save(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def flush(self) -> None:
        """Flush pending changes to the database without committing.

        Used by services that modify entity attributes after retrieval
        and need to persist those changes within the current transaction.
        """
        await self._session.flush()