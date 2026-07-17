"""
Database configuration and session management.
Provides async database connectivity with connection pooling.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from typing import AsyncGenerator
import logging

from oms.config.settings import config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class Database:
    """
    Manages database connections and sessions.
    Implements connection pooling and graceful degradation.
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        try:
            self.engine = create_async_engine(
                config.DATABASE_URL,
                echo=config.DATABASE_ECHO,
                pool_size=config.MAX_CONNECTIONS,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            self._initialized = True
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session.
        Implements fault detection and recovery.
        """
        if not self._initialized:
            await self.initialize()
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Check database connectivity for fault detection."""
        try:
            if not self._initialized or self.engine is None:
                logger.warning("Database not initialized")
                return False
            
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown database connections."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")


db = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database sessions."""
    async for session in db.get_session():
        yield session
