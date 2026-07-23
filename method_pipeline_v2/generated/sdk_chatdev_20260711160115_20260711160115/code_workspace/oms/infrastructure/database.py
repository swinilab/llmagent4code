# Async database engine and session factory using SQLAlchemy 2.0 + asyncpg.
#
# Pool sizing (HikariCP-style formula):
#   pool_size = Tn * (Cm - 1) + 1
#   where Tn = number of async workers (uvicorn workers * 1 async loop per worker)
#   Cm = max concurrent connections per worker (typically 1 for async)
#
#   Assumed: 16 CPU cores -> 8 uvicorn workers (async, each handles many concurrent reqs)
#   For async workers, the pool is shared across all workers via a single engine.
#   pool_size = 20 (covers 8 workers * ~2 concurrent DB calls each + headroom)
#   max_overflow = 10 (burst headroom)
#   Total max connections = 30
#
#   Connection timeout = 5s, pool recycle = 300s
from __future__ import annotations

import logging

import orjson
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from oms.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=5,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False,
    json_serializer=lambda o: orjson.dumps(o).decode(),
    json_deserializer=lambda o: orjson.loads(o),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncSession:
    """Yield an async DB session for write operations (commits on success).

    The async with context manager handles session.close() automatically.
    No manual close() in finally block needed — the context manager
    guarantees cleanup even on exception (NFR 2.2).
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session_readonly() -> AsyncSession:
    """Yield an async DB session for read-only operations (no commit).

    Includes rollback on error to prevent connection leaks (NFR 2.2).
    The async with context manager handles session.close() automatically.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (for development/testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose the engine."""
    await engine.dispose()
