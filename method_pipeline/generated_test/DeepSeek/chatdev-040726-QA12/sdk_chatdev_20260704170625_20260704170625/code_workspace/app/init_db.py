"""Database initializer — creates all tables on startup for development convenience.

In production, use Alembic migrations instead.
"""

from __future__ import annotations

import logging

from app.database import Base, engine

logger = logging.getLogger("oms.init_db")


async def create_tables() -> None:
    """Create all ORM-backed tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def drop_tables() -> None:
    """Drop all tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped.")