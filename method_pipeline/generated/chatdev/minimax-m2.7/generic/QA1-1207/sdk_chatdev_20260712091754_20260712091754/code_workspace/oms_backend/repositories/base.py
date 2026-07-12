"""
Base async repository — template method pattern for CRUD + list operations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Async CRUD repository with pagination and soft-delete support."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self, id: uuid.UUID) -> ModelType | None:
        """Get if not soft-deleted."""
        stmt = select(self.model).where(self.model.id == id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs) -> ModelType | None:
        kwargs["updated_at"] = datetime.utcnow()
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, id: uuid.UUID) -> bool:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(deleted_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        return True

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> tuple[list[ModelType], int]:
        """Paginated list with optional filters."""
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
            count_stmt = count_stmt.where(self.model.deleted_at.is_(None))

        if filters:
            for col, val in filters.items():
                if hasattr(self.model, col):
                    stmt = stmt.where(getattr(self.model, col) == val)
                    count_stmt = count_stmt.where(getattr(self.model, col) == val)

        # Count
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Order + paginate
        order_col = getattr(self.model, order_by, self.model.created_at)
        if descending:
            stmt = stmt.order_by(order_col.desc())
        else:
            stmt = stmt.order_by(order_col.asc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total
