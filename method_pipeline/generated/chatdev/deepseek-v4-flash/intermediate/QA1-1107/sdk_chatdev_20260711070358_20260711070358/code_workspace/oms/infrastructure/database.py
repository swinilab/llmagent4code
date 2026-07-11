"""
Database infrastructure using SQLAlchemy async with connection pooling.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from oms.config import settings


class Base(DeclarativeBase):
    pass


class Database:
    """Manages the async SQLAlchemy engine and session factory with bounded connection pooling."""

    def __init__(self, database_url: str = settings.database_url):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._database_url = database_url

    async def initialize(self) -> None:
        """Create the engine and session factory with explicit pool sizing.
        Idempotent: if the engine already exists, this is a no-op.
        """
        if self._engine is not None:
            return
        self._engine = create_async_engine(
            self._database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
            echo=settings.debug,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_all(self) -> None:
        """Create all tables defined by ORM models."""
        if self._engine is None:
            await self.initialize()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        """Drop all tables (for testing)."""
        if self._engine is None:
            await self.initialize()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around a series of operations."""
        if self._session_factory is None:
            await self.initialize()
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Dispose of the engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Singleton instance
database = Database()


async def init_db() -> None:
    """Initialize the database and create tables."""
    await database.initialize()
    await database.create_all()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with database.session() as session:
        yield session
