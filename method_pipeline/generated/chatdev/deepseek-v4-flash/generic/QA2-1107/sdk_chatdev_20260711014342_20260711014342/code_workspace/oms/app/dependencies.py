"""
FastAPI dependency injection - provides session-scoped services.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.models import engine

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, rolling back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
