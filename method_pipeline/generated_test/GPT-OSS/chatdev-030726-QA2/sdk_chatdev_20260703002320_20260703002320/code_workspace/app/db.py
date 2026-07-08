"""
SQLAlchemy engine and session management with deferred binding.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from functools import lru_cache
from app.config.settings import get_settings, reload_settings

Base = declarative_base()

@lru_cache()
def get_engine():
    """Create a SQLAlchemy engine using the latest settings.
    The engine is cached per process but cleared when configuration reloads.
    """
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

def get_session_factory():
    """Return a sessionmaker bound to the current engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

def get_db():
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Expose the engine for import elsewhere (e.g., migrations)
engine = get_engine()
