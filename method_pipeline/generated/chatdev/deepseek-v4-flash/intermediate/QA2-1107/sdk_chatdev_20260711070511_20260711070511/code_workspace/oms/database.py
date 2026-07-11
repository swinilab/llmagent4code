"""
Database engine and session management with WAL-mode durability for SQLite.
Uses a connection-pooling approach compatible with both SQLite and PostgreSQL.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from oms.config import settings

logger = logging.getLogger(__name__)

# Determine if we are using SQLite
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Engine creation
if _is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,  # verify connections before use (NFR 2.2)
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode and synchronous=NORMAL for crash-safe durability."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")       # atomic commits
        cursor.execute("PRAGMA synchronous=NORMAL;")     # balance speed/safety
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and closes it on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-manager version for use outside of request handlers."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call multiple times."""
    from oms.models.entities import (  # noqa: F401 – ensure models are registered
        CustomerModel,
        OrderModel,
        ProductModel,
        PaymentModel,
        InvoiceModel,
        OutboxMessage,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")
