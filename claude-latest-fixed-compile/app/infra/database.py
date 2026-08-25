"""Database engines.

Two engines are wired deliberately (NFR 1.2 Maintain Multiple Copies of Data):
  * ``primary_engine``  -> read/write, streaming-replication master.
  * ``replica_engine``  -> read-only, hot standby.

Both carry a statement timeout so a hung query surfaces as a detectable
exception rather than an indefinite stall (NFR 2.1 Exception Detection / timeout).
"""
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_engine(url: str, *, readonly: bool) -> Engine:
    engine = create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        future=True,
        connect_args={
            # libpq-level connect timeout: detects a dead node fast.
            "connect_timeout": 3,
            "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
        },
    )

    if readonly:

        @event.listens_for(engine, "begin")
        def _force_readonly_tx(conn):  # pragma: no cover - driver hook
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")

    return engine


primary_engine = _build_engine(settings.database_url, readonly=False)
replica_engine = _build_engine(settings.database_replica_url, readonly=True)

PrimarySession = sessionmaker(bind=primary_engine, expire_on_commit=False, future=True)
ReplicaSession = sessionmaker(bind=replica_engine, expire_on_commit=False, future=True)


@contextmanager
def unit_of_work() -> Iterator[Session]:
    """Transaction boundary on the primary (NFR 2.4 Transactions).

    Commits on success, rolls back on any exception. Every service mutation runs
    inside exactly one of these, so a partial workflow step can never persist.
    """
    session = PrimarySession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _open_replica_session() -> Session | None:
    """Open a replica session, eagerly proving the connection is usable.

    The probe is what makes the fallback real: SQLAlchemy connects lazily, so
    without an explicit round-trip a dead replica would only surface later,
    inside caller code, where it is no longer safely retryable.
    """
    session = ReplicaSession()
    try:
        session.execute(text("SELECT 1"))
        return session
    except Exception:
        logger.warning("replica unavailable; degrading reads to primary", exc_info=True)
        session.rollback()
        session.close()
        return None


@contextmanager
def read_session(prefer_replica: bool = True) -> Iterator[Session]:
    """Read-path session.

    Prefers the replica to shed load off the primary; falls back to the primary
    when the replica is unreachable (NFR 2.2 Graceful Degradation - the read
    still succeeds, only the load-shedding benefit is dropped). Exceptions raised
    by the caller propagate untouched; only connection failures trigger fallback.
    """
    session = _open_replica_session() if prefer_replica else None
    if session is None:
        session = PrimarySession()
    try:
        yield session
    finally:
        session.close()
