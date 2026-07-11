"""
Base repository with common CRUD operations.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common database operations."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> AsyncSession:
        """Expose the underlying async session for cross-repository operations."""
        return self._session

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get(self, id: str) -> ModelT | None:
        result = await self._session.execute(
            select(self._model).where(self._model.id == id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        result = await self._session.execute(
            select(self._model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count(self._model.id)))
        return result.scalar_one()

    async def update(self, id: str, **kwargs: Any) -> ModelT | None:
        instance = await self.get(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete(self, id: str) -> bool:
        instance = await self.get(id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
