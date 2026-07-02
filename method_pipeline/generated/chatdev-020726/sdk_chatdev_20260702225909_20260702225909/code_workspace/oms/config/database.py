"""
Database configuration and session management.

Provides async SQLAlchemy engine and session factory for the OMS.
Configured for production use with connection pooling and async support.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Database URL - using SQLite for local development, easily switchable to PostgreSQL
DATABASE_URL = "sqlite+aiosqlite:///./oms.db"

# Engine configuration for production
# For PostgreSQL in production, use:
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/oms"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Yields:
        AsyncSession: Database session instance
        
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_engine():
    """
    Get the database engine for direct access.
    
    Returns:
        AsyncEngine: Database engine instance
    """
    return engine


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This should be called once at application startup.
    For production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data. Use with caution.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
