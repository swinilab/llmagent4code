"""
Async database engine and session factory.
Connection pool sized per NFR 1.2 formula:
    pool_size = cores × 2 = 8 × 2 = 16
    max_overflow = 8 (burst headroom)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from oms.infrastructure.config import settings

engine = create_async_engine(
    settings.db_url,
    pool_size=settings.db_pool_size,       # 16 — see NFR 1.2
    max_overflow=settings.db_max_overflow,  # 8
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency yielding a DB session."""
    async with AsyncSessionLocal() as session:
        yield session
