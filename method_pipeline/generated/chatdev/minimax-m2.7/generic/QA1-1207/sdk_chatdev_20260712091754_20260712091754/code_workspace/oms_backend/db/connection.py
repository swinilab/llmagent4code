"""
Async PostgreSQL connection pool via `databases` + `asyncpg`.

NFR 1.2: Connection pooling (min 20 / max 100) ensures resource utilization
         without connection thrashing under concurrent load.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from databases import Database as BaseDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# ─────────────────────────────────────────────────────────────────────────────
# Engine + Session Factory (SQLAlchemy 2.0 async) — lazy init
# ─────────────────────────────────────────────────────────────────────────────

_async_engine = None
_async_session_factory = None
_db: BaseDatabase | None = None


def _get_engine_and_factory():
    global _async_engine, _async_session_factory
    if _async_engine is None:
        from oms_backend.core.config import get_settings
        settings = get_settings()
        _db_cfg = settings.database
        _async_engine = create_async_engine(
            _db_cfg.async_dsn,
            pool_size=_db_cfg.min_pool_size,
            max_overflow=_db_cfg.max_pool_size - _db_cfg.min_pool_size,
            pool_timeout=_db_cfg.pool_timeout,
            pool_pre_ping=True,
            echo=settings.app.debug,
        )
        _async_session_factory = sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_engine, _async_session_factory


def get_engine():
    eng, _ = _get_engine_and_factory()
    return eng


def get_session_factory():
    _, sess = _get_engine_and_factory()
    return sess


# ─────────────────────────────────────────────────────────────────────────────
# databases.Database wrapper (for raw SQL queries via `db.fetch_all()`)
# ─────────────────────────────────────────────────────────────────────────────

def get_database() -> BaseDatabase:
    global _db
    if _db is None:
        from oms_backend.core.config import get_settings
        settings = get_settings()
        _db_cfg = settings.database
        _db = BaseDatabase(_db_cfg.async_dsn, min_size=_db_cfg.min_pool_size, max_size=_db_cfg.max_pool_size)
    return _db


# ─────────────────────────────────────────────────────────────────────────────
# Session generator for dependency injection
# ─────────────────────────────────────────────────────────────────────────────

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async SQLAlchemy session."""
    _, session_factory = _get_engine_and_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside FastAPI dependency injection."""
    _, session_factory = _get_engine_and_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

async def check_db_health() -> bool:
    """Return True if the database is reachable."""
    try:
        db = get_database()
        await db.fetch_one(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db() -> None:
    global _db, _async_engine
    if _db is not None:
        await _db.disconnect()
        _db = None
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
