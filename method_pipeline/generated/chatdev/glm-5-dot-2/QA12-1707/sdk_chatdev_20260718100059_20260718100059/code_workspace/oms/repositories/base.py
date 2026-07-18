"""
Generic async repository base class.

Provides common CRUD operations using composition — entity-specific
repositories inherit this and add custom queries. Uses SQLAlchemy 2.0
async style with selectin loading for relationships.
"""
import uuid
from typing import Any, Generic, TypeVar, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing CRUD operations for any SQLAlchemy model.

    Subclasses set the ``model`` class attribute.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: str) -> ModelT | None:
        """Fetch a single record by primary key."""
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[Sequence[ModelT], int]:
        """
        Paginated fetch with optional equality filters.

        Returns (items, total_count).
        """
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                col = getattr(self.model, field, None)
                if col is not None and value is not None:
                    stmt = stmt.where(col == value)
                    count_stmt = count_stmt.where(col == value)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total

    async def create(self, **kwargs: Any) -> ModelT:
        """Insert a new record."""
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = str(uuid.uuid4())
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """Update an existing record with the given fields."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete a record."""
        await self.session.delete(instance)
        await self.session.flush()

    async def execute_query(self, stmt: Select) -> Any:
        """Execute a raw select statement (for custom queries in subclasses)."""
        result = await self.session.execute(stmt)
        return result