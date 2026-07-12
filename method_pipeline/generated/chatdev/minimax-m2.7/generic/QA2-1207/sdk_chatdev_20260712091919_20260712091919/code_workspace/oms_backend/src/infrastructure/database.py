"""
SQLAlchemy database setup with WAL mode for crash safety (NFR 2.3).
"""
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import json
import os

logger = logging.getLogger(__name__)

# Load config
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

db_config = config["database"]

# Create engine with proper settings for SQLite
engine = create_engine(
    db_config["url"],
    echo=db_config.get("echo", False),
    connect_args=db_config.get("connect_args", {}),
    poolclass=StaticPool,
    pool_pre_ping=db_config.get("pool_pre_ping", True)
)


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and foreign keys for crash safety."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
    logger.info("SQLite WAL mode enabled for crash-safe transactions")


# Register event to set pragmas on each connection
event.listen(engine, "connect", _set_sqlite_pragma)

Base = declarative_base()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from . import models  # noqa
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def check_db_health() -> dict:
    """Check database connectivity and integrity."""
    try:
        with engine.connect() as conn:
            # Check WAL mode
            result = conn.execute(text("PRAGMA journal_mode"))
            wal_mode = result.scalar()

            # Check sync
            result = conn.execute(text("PRAGMA synchronous"))
            sync_mode = result.scalar()

            # Check for any unrecovered transactions
            result = conn.execute(text("PRAGMA quick_check"))
            integrity = result.scalar()

            return {
                "status": "healthy",
                "wal_mode": wal_mode,
                "sync_mode": sync_mode,
                "integrity": integrity
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
