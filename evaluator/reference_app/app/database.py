"""Database access with timeout detection and bounded retry.

Three availability tactics meet at this boundary, and keeping them distinct is
the whole job:

  ASR-A1  a statement that runs too long is abandoned, not waited out
  ASR-A2  a transient failure is retried, up to a fixed ceiling
  ASR-A3  an unreachable database is reported as such, not as slowness

Fault classification is what separates them. A timeout and a refused connection
both mean "no answer", but only one of them should be retried and they must not
report the same code -- an evaluator that saw DEPENDENCY_TIMEOUT for a severed
connection could not tell the timeout tactic from the degradation tactic.

The timeout has two halves, because slowness has two sources and PostgreSQL can
only see one of them. `statement_timeout` bounds how long the server spends
executing, so the server abandons work rather than being left running while its
caller walks away. `with_deadline` bounds the caller's wait, which is what
catches latency in the network -- there the query itself is fast and only the
bytes are slow, so the server-side limit never fires at all.
"""

from __future__ import annotations


import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypeVar

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from .cache import DependencyUnavailable
from .config import settings
from .observability import (
    DEPENDENCY_TIMEOUT,
    DEPENDENCY_UNAVAILABLE,
    ControlledError,
    log_event,
    metrics,
)

T = TypeVar("T")


class TransientDatabaseError(RuntimeError):
    """A failure worth retrying: the next attempt may legitimately succeed."""


class DatabaseTimeout(RuntimeError):
    """A statement exceeded its configured time limit."""


_IS_POSTGRES = settings.database_url.startswith("postgresql")

_TIMEOUT_S = max(1, round(settings.db_operation_timeout_ms / 1000))

# The timeout controls below are PostgreSQL features. They are applied only on
# that dialect so the same code can also run against SQLite for fast local
# checks -- the deployed configuration, and every timing scenario, is Postgres.
_engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if _IS_POSTGRES:
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=10,
        connect_args={
            # Bound connection establishment: during an outage an attempt would
            # otherwise hang far longer than the per-operation budget allows.
            "connect_timeout": _TIMEOUT_S,
            # Bound execution at the server. This is one of two limits; see
            # with_deadline for why server-side alone is not sufficient.
            "options": f"-c statement_timeout={settings.db_operation_timeout_ms}",
        },
    )

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

if _IS_POSTGRES:

    @event.listens_for(engine, "connect")
    def _apply_statement_timeout(dbapi_connection: Any, _record: Any) -> None:
        """Bound every statement on this connection at the database itself.

        Enforced by PostgreSQL rather than by racing a Python timer, so the
        server actually stops working on the query instead of being abandoned
        while it keeps going.
        """
        with dbapi_connection.cursor() as cur:
            cur.execute(f"SET statement_timeout = {settings.db_operation_timeout_ms}")


@contextmanager
def session_scope() -> Iterator[Session]:
    """A transaction that commits on success and rolls back on any failure.

    ASR-A4 depends on there being exactly one commit for the whole unit of
    work, so nothing inside may commit on its own.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── fault classification ──────────────────────────────────────────────────

_TIMEOUT_MARKERS = (
    "statement timeout",
    "canceling statement",
    "query_canceled",
    # A connection that times out while being established is still a timeout.
    # Injected network latency delays the handshake as much as the query, so
    # classifying this as unavailability would report a slow dependency as an
    # absent one and make ASR-A1 indistinguishable from ASR-A3.
    "connection timeout expired",
    "timeout expired",
)

# Ordered deliberately: a message can match both families -- "connection
# timeout expired" contains "connection" -- so the markers above are tested
# first and only genuine unreachability falls through to these.
_UNAVAILABLE_MARKERS = (
    "connection refused",
    "could not translate host name",
    "server closed the connection",
    "connection reset",
    "no route to host",
    "terminating connection",
    "eof detected",
    "could not connect",
)


def classify(exc: Exception) -> Exception:
    """Translate a driver error into the specific failure it represents.

    Getting this wrong in either direction is a real defect: retrying a refused
    connection wastes the attempt budget on something that cannot succeed, and
    reporting a timeout as unavailability hides which fault was detected.
    """
    message = str(exc).lower()
    if any(m in message for m in _TIMEOUT_MARKERS):
        return DatabaseTimeout(str(exc))
    if any(m in message for m in _UNAVAILABLE_MARKERS):
        return DependencyUnavailable(str(exc))
    if isinstance(exc, OperationalError):
        # Operational errors that are neither of the above are the transient
        # class: deadlocks, serialisation failures, a dropped pool connection.
        return TransientDatabaseError(str(exc))
    return exc


def to_controlled(exc: Exception) -> ControlledError:
    """Map an internal failure to the response the client should see."""
    if isinstance(exc, DatabaseTimeout):
        code = DEPENDENCY_TIMEOUT
        if settings.defect_wrong_error_code:
            code = DEPENDENCY_UNAVAILABLE
        return ControlledError(504, code, "database operation exceeded its time limit")
    if isinstance(exc, DependencyUnavailable):
        code = DEPENDENCY_UNAVAILABLE
        if settings.defect_wrong_error_code:
            code = DEPENDENCY_TIMEOUT
        return ControlledError(503, code, "database is unavailable")
    return ControlledError(503, DEPENDENCY_UNAVAILABLE, "database operation failed")


# ── bounded retry ─────────────────────────────────────────────────────────


# Sized far above the in-flight limit. Requests wait here for a worker, and a
# request queued behind a slow neighbour inherits its delay -- which turns a
# 200 ms cache read into a multi-second one and shows up as a latency failure
# nowhere near the code responsible. The pool must never be the bottleneck.
_deadline_pool = ThreadPoolExecutor(
    max_workers=max(128, settings.max_in_flight_requests * 8),
    thread_name_prefix="db-deadline",
)


def with_deadline(operation: Callable[[], T], seconds: float) -> T:
    """Run `operation` on a worker thread and stop waiting after `seconds`.

    Two things can make a database call slow, and only one of them is visible
    to PostgreSQL. `statement_timeout` bounds execution, but latency injected
    into the network leaves execution fast while the bytes crawl -- the server
    finishes promptly and the caller still waits out the full delay.

    This bounds the wait itself, so the caller is released whichever layer is
    slow. It is a genuine detection point rather than a client-side convenience:
    `statement_timeout` remains set, so the server also abandons work it is
    still doing, and the two together cover both failure shapes.

    The abandoned thread is left to finish on its own. Its connection is
    reclaimed by the pool, and holding the request open to tidy up would defeat
    the purpose of having a deadline at all.

    Note that `operation` runs on a bare worker thread with no ContextVars
    inherited from the caller. Anything per-request the operation needs must be
    captured before it is submitted -- see `with_retry`, which reads the fault
    state on the calling thread and hands the operation a plain closure.

    Passing a contextvars.Context here would be the obvious alternative and does
    not work: a Context cannot be entered twice, so once an attempt times out
    the abandoned thread still holds it and every later attempt fails with
    "cannot enter context" instead of retrying.
    """
    future = _deadline_pool.submit(operation)
    try:
        return future.result(timeout=seconds)
    except FutureTimeout:
        future.cancel()
        raise DatabaseTimeout(f"database operation exceeded {seconds:.1f}s") from None


def with_retry(operation: Callable[[], T], *, count_attempts: bool = False) -> T:
    """Run `operation`, retrying only transient faults, up to DB_MAX_ATTEMPTS.

    Timeouts are retried as well -- the specification's timing budget assumes
    three attempts -- but backoff is skipped after one, since the timeout has
    already provided the delay that backoff exists to create.

    A refused connection is not retried at all: the database is gone, and three
    attempts would merely spend the budget before reporting the same outcome.
    """
    attempts = settings.db_max_attempts
    last: Exception | None = None
    # The operation is expected to bound itself with with_deadline, applying
    # the limit around the database call only. Wrapping the whole operation
    # here instead would put per-request state -- notably the injected fault
    # counter, which lives in a ContextVar -- on the far side of a thread
    # boundary that does not carry it.
    for attempt in range(1, attempts + 1):
        if count_attempts:
            metrics.increment("db_product_read_attempts_total")
        try:
            return operation()
        except DependencyUnavailable:
            raise
        except (TransientDatabaseError, DatabaseTimeout) as exc:
            last = exc
            if isinstance(exc, DatabaseTimeout):
                metrics.increment("timeouts_total")
            if attempt >= attempts:
                break
            metrics.increment("retry_attempts_total")
            log_event(
                "retry_attempt",
                attempt=attempt,
                next_attempt=attempt + 1,
                reason=type(exc).__name__,
            )
            if not isinstance(exc, DatabaseTimeout):
                time.sleep(settings.db_retry_backoff_ms / 1000.0)
        except (DBAPIError, OperationalError) as exc:
            classified = classify(exc)
            if isinstance(classified, DependencyUnavailable):
                raise classified from exc
            last = classified
            if isinstance(classified, DatabaseTimeout):
                metrics.increment("timeouts_total")
            if attempt >= attempts:
                break
            metrics.increment("retry_attempts_total")
            log_event("retry_attempt", attempt=attempt, reason=type(classified).__name__)
            if not isinstance(classified, DatabaseTimeout):
                time.sleep(settings.db_retry_backoff_ms / 1000.0)

    assert last is not None
    raise last


def database_reachable() -> bool:
    """Cheap liveness probe used by readiness, bounded so it cannot hang."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
