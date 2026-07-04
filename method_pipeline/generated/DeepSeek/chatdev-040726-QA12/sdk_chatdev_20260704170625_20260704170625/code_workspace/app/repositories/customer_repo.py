"""Customer repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.entities import CustomerEntity
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[CustomerEntity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CustomerEntity)