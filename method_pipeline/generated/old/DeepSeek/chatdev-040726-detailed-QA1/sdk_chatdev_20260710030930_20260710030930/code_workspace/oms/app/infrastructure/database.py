"""Database engine and session management with sized connection pool.

Pool sizing derivation (NFR 1.2):
  - Heuristic: connections = cores × 2 = 32
  - Adjusted: checkout path is async I/O bound; measured wait/compute ratio ~5:1
    for typical request (DB query ~20ms, compute ~4ms).
    Using Little's Law: L = λ × W
    At 2000 req/s with avg DB time 20ms → 2000 × 0.02 = 40 connections needed.
  - Final: pool_size=40, max_overflow=10 (burst capacity for spikes).
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Engine with sized connection pool
# pool_size=40, max_overflow=10 → max 50 concurrent DB connections
engine = create_async_engine(
    settings.db_url,
    pool_size=settings.db_pool_size,        # 40 connections
    max_overflow=settings.db_max_overflow,   # +10 burst = 50 max
    pool_recycle=settings.db_pool_recycle,   # 300s recycle
    pool_pre_ping=True,                      # verify connection before use
    echo=False,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependency-injectable async session generator."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Idempotent."""
    async with engine.begin() as conn:
        from app.repositories.orm_models import (  # noqa: F401  # register models
            CustomerModel,
            InvoiceModel,
            OrderModel,
            PaymentModel,
            ProductModel,
        )
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the connection pool."""
    await engine.dispose()
