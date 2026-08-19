"""
Database connection and session management
Implements NFR 1.2 (multiple copies via caching) and NFR 2.1 (exception detection)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from oms_backend.config.settings import get_settings

settings = get_settings()

# Async engine for NFR 2.1 timeout handling
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"timeout": settings.db_timeout_seconds}
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Database:
    """Database connection manager with retry logic for NFR 2.1"""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = async_session_maker
        self._cache = {}  # Simple in-memory cache for NFR 1.2
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_delay_seconds),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        reraise=True
    )
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with retry logic for fault tolerance"""
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def get_cached(self, key: str) -> any:
        """Get value from cache (NFR 1.2 - multiple copies of data)"""
        return self._cache.get(key)
    
    def set_cached(self, key: str, value: any, ttl: int = 300) -> None:
        """Set value in cache with TTL (NFR 1.2 - multiple copies of data)"""
        self._cache[key] = {
            "value": value,
            "expires_at": asyncio.get_event_loop().time() + ttl
        }
    
    def invalidate_cache(self, pattern: str = None) -> None:
        """Invalidate cache entries"""
        if pattern:
            self._cache = {k: v for k, v in self._cache.items() if not k.startswith(pattern)}
        else:
            self._cache.clear()
    
    async def init_db(self) -> None:
        """Initialize database tables"""
        from oms_backend.domain.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Close database connections"""
        await engine.dispose()


# Global database instance
db = Database()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async for session in db.get_session():
        yield session
