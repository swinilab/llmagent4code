"""
Async database engine and session management with connection pooling.

Connection pool sizing (NFR 1.2):
  - Target hardware: multi-core CPU, 98 GB RAM.
  - PostgreSQL recommended pool size formula:
      pool_size = (core_count * 2) + effective_spindle_count
  - With 8+ cores and SSD, we use pool_size=20, max_overflow=10.
  - This keeps ~30 concurrent DB connections, well within PostgreSQL limits
    and avoids over-saturating the database.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
    create_async_engine,
)

from oms.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# Connection pool sized per NFR 1.2: 20 core connections + 10 overflow.
# Using asyncpg driver for true async I/O.
_engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,          # verify connections before use (NFR 2.2)
    pool_recycle=3600,           # recycle connections every hour
    echo=settings.debug,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
_SessionFactory = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations.

    Commits on success, rolls back on exception.
    """
    async with _SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_readonly_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a read-only session (no auto-commit)."""
    async with _SessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Health-check: execute a simple query (NFR 2.2)."""
    try:
        async with _SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db_pool() -> None:
    """Dispose of the connection pool (graceful shutdown)."""
    await _engine.dispose()
