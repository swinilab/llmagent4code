"""
Payment repository.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Payment)
