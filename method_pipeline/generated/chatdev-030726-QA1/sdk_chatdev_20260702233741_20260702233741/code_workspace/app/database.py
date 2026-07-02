# app/database.py
"""Database connection and session management using SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# For local development we use SQLite; in production replace with PostgreSQL URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./oms.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency that provides a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
