"""
Database engine, session factory, and base declarative model.

Connection pooling (pool_size=20, max_overflow=10) satisfies NFR 1.2
by reusing connections and avoiding the overhead of establishing new
connections under high concurrency.  pool_pre_ping=True ensures stale
connections are detected and replaced before use.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session.

    The session is closed after the request completes, returning the
    underlying connection to the pool for reuse (NFR 1.2).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
