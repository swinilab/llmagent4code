"""Database connection and session management using SQLModel."""

from sqlmodel import SQLModel, create_engine, Session
from .config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Create database tables based on SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Provide a new database session for dependency injection."""
    with Session(engine) as session:
        yield session
