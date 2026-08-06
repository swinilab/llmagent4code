"""
Database infrastructure
SQLAlchemy ORM setup with connection pooling and transaction management
"""
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from oms_backend.config import settings


# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # NFR 2.1: Exception detection - detect stale connections
    echo=settings.debug,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    Yields session and ensures cleanup.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a new database session.
    For use outside of FastAPI dependency injection.
    
    Returns:
        Database session
    """
    return SessionLocal()


@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """
    Connection event handler.
    NFR 2.1: Exception detection - log connection issues
    """
    pass  # Can add logging here if needed


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """
    Checkout event handler.
    NFR 2.3: State Resynchronization - verify connection is valid
    """
    pass  # Connection is verified by pool_pre_ping


class TransactionManager:
    """
    Transaction manager for NFR 2.4: Transactions
    Ensures ACID properties for database operations
    """
    
    def __init__(self, session: Session):
        """
        Initialize transaction manager.
        
        Args:
            session: Database session
        """
        self.session = session
        self._nested_level = 0
        
    def begin(self):
        """Begin a new transaction"""
        if self._nested_level == 0:
            self.session.begin()
        else:
            self.session.begin_nested()
        self._nested_level += 1
        
    def commit(self):
        """Commit the current transaction"""
        if self._nested_level > 0:
            self._nested_level -= 1
            if self._nested_level == 0:
                self.session.commit()
                
    def rollback(self):
        """Rollback the current transaction"""
        if self._nested_level > 0:
            self._nested_level = 0
            self.session.rollback()
    
    def __enter__(self):
        self.begin()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
