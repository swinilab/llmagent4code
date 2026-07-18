"""
Generic async repository base with common CRUD operations.

ADR-004: Repository pattern over raw SQLAlchemy queries.
  Decision: Thin async repository wrapping SQLAlchemy session.
  Context: NFR 1.1 (Response Time) — repositories enable query optimisation in one place.
  Alternatives: (a) direct session in services — couples business logic to ORM;
    (b) raw SQL — loses type safety.
  Consequences: Adds a layer but isolates data-access tuning.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository for a single entity type."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: str) -> ModelT | None:
        """Fetch a single entity by primary key."""
        return await self.session.get(self.model, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """List entities with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Remove an entity."""
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self) -> int:
        """Return total row count."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()
