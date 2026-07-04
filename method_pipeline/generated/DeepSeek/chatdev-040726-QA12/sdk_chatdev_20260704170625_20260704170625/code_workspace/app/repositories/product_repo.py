"""Product repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.entities import ProductEntity
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[ProductEntity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductEntity)