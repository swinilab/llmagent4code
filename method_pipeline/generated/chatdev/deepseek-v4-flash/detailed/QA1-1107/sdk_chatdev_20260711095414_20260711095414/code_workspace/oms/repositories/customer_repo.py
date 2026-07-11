"""
Customer repository.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from oms.infrastructure.entities import CustomerModel
from oms.repositories import BaseRepository


class CustomerRepository(BaseRepository[CustomerModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CustomerModel)
