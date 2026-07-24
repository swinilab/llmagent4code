"""
Customer repository.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Customer)
