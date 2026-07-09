"""
Async database engine and session factory with connection pooling.

Pool sizing rationale (NFR 1.2):
  Target hardware: 4 CPU cores, 98 GB RAM.
  PostgreSQL can handle ~active_connections = (2 * core_count) + effective_spindle_count.
  We set pool_size=20, max_overflow=10 → max 30 concurrent connections.
  Each connection uses ~10 MB → 300 MB total, well within budget.
  The async driver (asyncpg) uses non-blocking I/O so a single worker can
  multiplex many DB operations without holding a thread per connection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.db_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
