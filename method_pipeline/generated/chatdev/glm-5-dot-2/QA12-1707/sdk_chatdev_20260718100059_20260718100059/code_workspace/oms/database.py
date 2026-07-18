"""
Async database engine, session factory, and lifecycle helpers.

Uses SQLite with WAL mode for crash-safe durability (NFR 2.3).
The engine is created once at startup and shared via a global factory.
"""
import os
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from oms.config import settings


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""
    pass


engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_sqlite_dir(database_url: str) -> None:
    """
    Ensure the parent directory of a file-based SQLite database exists.

    SQLite cannot create the database file if its containing directory is
    missing. For a relative path like ``./data/oms.db`` this guarantees the
    ``data/`` directory is present before the engine opens the file, which
    keeps the persisted database inside a mounted volume (NFR 2.3).
    """
    if not database_url.startswith("sqlite"):
        return
    parsed = urlparse(database_url)
    # SQLAlchemy sqlite URLs use a host/path convention:
    #   sqlite+aiosqlite:///./data/oms.db  ->  parsed.path == "/./data/oms.db"
    #   sqlite+aiosqlite:////abs/data/oms.db -> parsed.path == "/abs/data/oms.db"
    raw_path = parsed.path
    if not raw_path:
        return
    # Strip the leading slash that urlparse adds for the "no host" form so a
    # relative path like "/./data/oms.db" becomes "./data/oms.db".
    if raw_path.startswith("/") and not raw_path.startswith("//"):
        candidate = raw_path.lstrip("/")
    else:
        candidate = raw_path
    if not candidate:
        return
    db_path = os.path.abspath(candidate)
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


async def init_db() -> AsyncEngine:
    """
    Create the async engine, enable WAL mode for durability,
    create all tables, and initialise the session factory.

    Returns the engine so callers can dispose it on shutdown.
    """
    global engine, async_session_factory

    _ensure_sqlite_dir(settings.database_url)

    engine = create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )

    # Enable WAL mode for crash-safe writes (NFR 2.3 State Preservation)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.exec_driver_sql("PRAGMA busy_timeout=5000")

    # Import models so they register on Base.metadata
    from oms.models import customer, product, order, payment, invoice  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine


async def get_session() -> AsyncSession:
    """
    FastAPI dependency that yields an async session.

    The session is closed automatically when the generator resumes.
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    async with async_session_factory() as session:
        yield session


async def dispose_db() -> None:
    """Dispose the engine connection pool on shutdown.

    Both the engine and the shared session factory are cleared so that the
    ``get_session()`` guard fires cleanly after disposal. This keeps the
    disposal symmetric with :func:`init_db` (which declares both names global)
    and preserves the NFR 2.3 restart/recovery invariant: after disposal, any
    request that arrives before re-initialisation receives the intended
    "Database not initialised" message instead of opening a session on a
    disposed engine.
    """
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None