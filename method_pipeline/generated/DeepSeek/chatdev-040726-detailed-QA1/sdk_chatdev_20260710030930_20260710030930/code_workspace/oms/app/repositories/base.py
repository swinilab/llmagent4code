"""Base repository with common CRUD operations."""

import json
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository with common database operations."""

    def __init__(self, model_class: type[T], session: AsyncSession) -> None:
        self.model_class = model_class
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get an entity by its UUID primary key."""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """List entities with pagination."""
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, instance: T) -> T:
        """Save a new entity to the database."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, entity_id: UUID, data: dict[str, Any]) -> Optional[T]:
        """Update an entity by ID with the given data dict."""
        stmt = (
            update(self.model_class)
            .where(self.model_class.id == entity_id)  # type: ignore[attr-defined]
            .values(**data)
            .returning(self.model_class)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by ID. Returns True if deleted."""
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    @staticmethod
    def serialize_json_list(items: list[Any]) -> str:
        """Serialize a list to JSON string for storage."""
        return json.dumps([item.model_dump() if hasattr(item, "model_dump") else item for item in items], default=str)

    @staticmethod
    def deserialize_json_list(data: str) -> list[Any]:
        """Deserialize a JSON string to a list."""
        if not data:
            return []
        return json.loads(data)
