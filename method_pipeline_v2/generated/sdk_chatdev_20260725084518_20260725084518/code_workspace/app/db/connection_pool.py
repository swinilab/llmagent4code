"""
Database connection pool with fault detection and recovery
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.config.settings import Settings

settings = Settings()

_engine = None
_session_factory = None


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass


@retry(
    stop=stop_after_attempt(settings.retry_max_attempts),
    wait=wait_fixed(settings.retry_delay_seconds),
    retry=retry_if_exception_type(DatabaseConnectionError),
    reraise=True,
)
async def connect_with_retry():
    """Connect to database with retry logic for fault recovery"""
    global _engine, _session_factory
    try:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return True
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to connect to database: {e}")


async def init_db():
    """Initialize database connection pool"""
    await connect_with_retry()
    await create_tables()


async def close_db():
    """Close database connection pool"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session from pool with connection validation"""
    if _session_factory is None:
        await connect_with_retry()
    
    async with _session_factory() as session:
        try:
            # Ping to verify connection is alive
            await session.execute(select(1))
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


async def health_check() -> bool:
    """Check if database connection is healthy"""
    if _engine is None:
        return False
    try:
        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def create_tables():
    """Create database tables"""
    from app.db.tables import Base
    if _engine:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
