from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyUnitOfWork:
    """Owns explicit SQLAlchemy transaction boundaries for service operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("no unit-of-work transaction is active")
        return self._session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Commit all enclosed changes atomically, or roll all of them back."""

        if self._session is not None:
            raise RuntimeError("unit-of-work transactions cannot be nested")
        async with self._session_factory() as session:
            self._session = session
            try:
                async with session.begin():
                    yield session
            finally:
                self._session = None

