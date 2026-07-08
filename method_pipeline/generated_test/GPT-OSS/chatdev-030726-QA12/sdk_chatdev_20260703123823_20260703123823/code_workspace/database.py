"""Database module: creates SQLAlchemy engine and session factory.
Uses request‑scoped engine and session to support deferred binding of DATABASE_URL.
"""
import sqlalchemy
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_settings

def get_engine():
    """Create a new SQLAlchemy engine using the current DATABASE_URL.
    Called per request to respect dynamic configuration changes.
    """
    settings = get_settings()
    return sqlalchemy.create_engine(settings.DATABASE_URL, echo=False, future=True)

# Dependency that yields a DB session per request
def get_db():
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()
