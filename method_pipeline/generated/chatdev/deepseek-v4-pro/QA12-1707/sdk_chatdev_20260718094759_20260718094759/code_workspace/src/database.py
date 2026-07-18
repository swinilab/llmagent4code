"""
Database engine and session factory.

ADR-002: Use SQLAlchemy 2.0 async with aiosqlite for local deployment.
  Decision: Async SQLAlchemy + aiosqlite (WAL mode).
  Context: NFR 1.2 (Concurrency), NFR 2.3 (State Preservation).
  Alternatives: (a) PostgreSQL — heavier local setup; (b) raw aiosqlite — no ORM.
  Consequences: SQLite has limited concurrent writes but WAL mode mitigates this.
    Zero-install local deployment is the primary benefit.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.config import settings

_engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

_async_session_factory = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (FastAPI dependency)."""
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    from src.models.base import Base  # noqa: PLC0415
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    # Enable WAL mode for better concurrent read performance (NFR 1.2)
    async with _engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")


async def dispose_engine() -> None:
    """Gracefully dispose the engine on shutdown."""
    await _engine.dispose()
