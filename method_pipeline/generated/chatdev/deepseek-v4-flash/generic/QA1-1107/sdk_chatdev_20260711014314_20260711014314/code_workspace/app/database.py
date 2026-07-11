"""
Database engine, session factory, and base model.
Uses async SQLAlchemy with aiosqlite for local development.
"""
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Uses async generator pattern for proper session lifecycle management.
    The session is committed after the response is sent, and rolled back
    on any exception.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        logger.exception("Database session error, rolling back")
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Create all tables on startup (for local dev; use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
