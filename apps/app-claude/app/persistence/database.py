"""The single database boundary: engine, timeout, retry, and fault classification.

This module is the only place the application talks to PostgreSQL, so the
availability tactics are implemented once here and apply to every entity, every
read and write, and the connection-acquisition step:

* ASR-A1 `Availability > Detect Faults > Timeout` - `_run_attempt` bounds each
  attempt with DB_OPERATION_TIMEOUT_MS, and the driver is additionally
  configured with matching server-side and connect timeouts.
* ASR-A2 `Availability > Recover from Faults > Preparation and Repair > Retry` -
  `run_with_resilience` retries only classified-retryable faults, at most
  DB_MAX_ATTEMPTS times, with bounded backoff.
* ASR-A3 - connection-level failures are classified as DEPENDENCY_UNAVAILABLE,
  distinct from the DEPENDENCY_TIMEOUT raised when attempts exceed their limit.

Sessions are synchronous (psycopg) and executed on a worker thread by the API
layer, which keeps the per-attempt timeout enforceable without leaving a
half-cancelled asyncio task behind.
"""

from __future__ import annotations

import contextvars
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
    TimeoutError as SATimeoutError,
)
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.errors import (
    ControlledError,
    DependencyTimeoutError,
    DependencyUnavailableError,
    DomainError,
    TransactionFailedError,
)
from app.core.logging import log_event
from app.core.metrics import metrics
from app.core.test_hooks import InjectedTransactionFault, InjectedTransientDbError

T = TypeVar("T")

# Per-attempt statement timeout is pushed down to the server as well, so a query
# that has already reached PostgreSQL is cancelled there rather than being
# abandoned by the client.
_STATEMENT_TIMEOUT_MS = settings.db_operation_timeout_ms

engine = create_engine(
    settings.database_url,
    pool_pre_ping=False,
    pool_size=settings.max_in_flight_requests + 5,
    max_overflow=10,
    pool_timeout=settings.db_operation_timeout_seconds,
    pool_recycle=300,
    connect_args={
        "connect_timeout": max(1, round(settings.db_operation_timeout_seconds)),
        "options": f"-c statement_timeout={_STATEMENT_TIMEOUT_MS}",
    },
    future=True,
)

SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

# Attempts run on this pool so that a hung attempt can be abandoned by the
# caller once its per-attempt deadline passes.
_attempt_executor = ThreadPoolExecutor(
    max_workers=settings.max_in_flight_requests * 2 + 8,
    thread_name_prefix="db-attempt",
)


def _is_timeout_error(exc: BaseException) -> bool:
    """True when the failure is an exceeded time limit rather than unreachability."""
    if isinstance(exc, (SATimeoutError, FuturesTimeoutError)):
        return True
    message = str(exc).lower()
    if isinstance(exc, (OperationalError, DBAPIError)):
        return (
            "statement timeout" in message
            or "canceling statement due to" in message
            or "query_canceled" in message
        )
    return False


def _is_unavailable_error(exc: BaseException) -> bool:
    """True when the database could not be reached at all."""
    if isinstance(exc, (DisconnectionError, InterfaceError)):
        return True
    if isinstance(exc, (OperationalError, DBAPIError)):
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "connection refused",
                "connection reset",
                "could not connect",
                "server closed the connection",
                "connection already closed",
                "no connection to the server",
                "terminating connection",
                "is not currently accepting",
                "connection timed out",
                "eof detected",
                "network is unreachable",
                "host is unreachable",
                "broken pipe",
            )
        )
    return False


def is_retryable(exc: BaseException) -> bool:
    """Retryable-fault classification for the bounded retry policy.

    Only transient faults qualify. Validation failures, 404s, and 409s never
    reach this function - they are domain errors raised above the database
    boundary - which is what keeps retry_attempts_total flat for those cases.
    """
    if isinstance(exc, InjectedTransientDbError):
        return True
    if isinstance(exc, InjectedTransactionFault):
        return False
    return _is_timeout_error(exc) or _is_unavailable_error(exc)


def _classify(exc: BaseException) -> Exception:
    """Map an exhausted attempt to the correct controlled error."""
    if _is_timeout_error(exc) or isinstance(exc, InjectedTransientDbError):
        return DependencyTimeoutError()
    if _is_unavailable_error(exc):
        return DependencyUnavailableError()
    return DependencyUnavailableError()


class DependencyHealthGate:
    """Tracks whether the database is reachable so callers can fail fast.

    This is what keeps a dependency outage from degrading into an overload
    condition (ASR-A3). Without it every request would re-pay the full
    connection-failure latency before its degraded read could be served, which
    both blows the warmed-read latency budget and holds admitted slots open.

    After `_probe_interval_seconds` a single caller is allowed through to test
    whether the database has recovered, so normal service resumes automatically.
    """

    def __init__(self, probe_interval_seconds: float = 1.0) -> None:
        self._lock = threading.Lock()
        self._healthy = True
        self._unhealthy_since = 0.0
        self._last_probe = 0.0
        self._probe_interval_seconds = probe_interval_seconds

    def should_fail_fast(self) -> bool:
        """True whenever the database is known unreachable.

        Requests never carry the recovery probe themselves: a probe pays the full
        connection-failure latency, and charging that to a user-facing read would
        break the warmed-read latency budget of ASR-A3. Recovery is detected by
        the background prober below instead.
        """
        with self._lock:
            return not self._healthy

    def record_success(self) -> None:
        with self._lock:
            if not self._healthy:
                log_event("dependency_recovered")
            self._healthy = True

    def record_unavailable(self) -> None:
        with self._lock:
            if self._healthy:
                self._healthy = False
                self._unhealthy_since = time.monotonic()
                self._last_probe = time.monotonic()
                log_event("dependency_unavailable", error_code="DEPENDENCY_UNAVAILABLE")

    @property
    def healthy(self) -> bool:
        with self._lock:
            return self._healthy


health_gate = DependencyHealthGate()


def _recovery_prober() -> None:
    """Detect database recovery off the request path.

    While the gate reports unhealthy this probes the database on a fixed
    interval; the first successful probe clears the gate, so normal service
    resumes automatically without any request having paid probe latency.
    """
    while True:
        try:
            if not health_gate.healthy:
                def probe() -> None:
                    with SessionFactory() as session:
                        session.execute(text("SELECT 1"))

                try:
                    _run_attempt(probe, settings.db_operation_timeout_seconds)
                    health_gate.record_success()
                except BaseException:  # noqa: BLE001 - still down; keep probing
                    pass
        except BaseException:  # noqa: BLE001 - the prober must never die
            pass
        time.sleep(0.5)


_prober_thread = threading.Thread(
    target=_recovery_prober, name="db-recovery-prober", daemon=True
)
_prober_thread.start()


def _run_attempt(operation: Callable[[], T], timeout_seconds: float) -> T:
    """Execute one attempt under the configured per-attempt time limit.

    The caller's contextvars are copied into the worker thread. Without this the
    per-request injected-fault directive would be invisible at the database
    boundary, because a thread does not inherit the context of whoever submitted
    its work.
    """
    context = contextvars.copy_context()
    future = _attempt_executor.submit(context.run, operation)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        future.cancel()
        raise


def run_with_resilience(
    operation: Callable[[], T],
    *,
    operation_name: str,
    retryable: bool = True,
    on_attempt: Callable[[], None] | None = None,
) -> T:
    """Run a database operation under the timeout + bounded-retry policy.

    `retryable=False` is the safety valve required by ASR-A2: an operation whose
    effect may already have been applied at the database is never blindly
    re-executed. Callers pass False for any write that is not known to have been
    rolled back.
    """
    attempts = settings.db_max_attempts if retryable else 1
    last_exc: BaseException | None = None

    # Fail fast while the database is known unreachable, so a degraded read can
    # be served immediately and a write is refused without occupying its
    # admitted slot for the full connection timeout.
    if health_gate.should_fail_fast():
        raise DependencyUnavailableError()

    for attempt in range(1, attempts + 1):
        if on_attempt is not None:
            on_attempt()
        try:
            result = _run_attempt(operation, settings.db_operation_timeout_seconds)
            health_gate.record_success()
            return result
        except (DomainError, ControlledError):
            # Reaching a business outcome proves the database answered.
            health_gate.record_success()
            # Business outcomes (400/404/409) and already-classified controlled
            # failures are not infrastructure faults: they are never retried and
            # never reclassified as a dependency problem.
            raise
        except BaseException as exc:  # noqa: BLE001 - classified immediately below
            last_exc = exc

            if _is_unavailable_error(exc):
                health_gate.record_unavailable()

            timed_out = _is_timeout_error(exc) or isinstance(exc, InjectedTransientDbError)
            if timed_out:
                metrics.increment("timeouts_total")
                log_event(
                    "db_operation_timeout",
                    operation=operation_name,
                    attempt=attempt,
                    timeout_ms=settings.db_operation_timeout_ms,
                    error_code="DEPENDENCY_TIMEOUT",
                )

            if not retryable or not is_retryable(exc) or attempt >= attempts:
                break

            metrics.increment("retry_attempts_total")
            log_event(
                "db_retry_attempt",
                operation=operation_name,
                attempt=attempt + 1,
                max_attempts=attempts,
                reason=type(exc).__name__,
            )

            # Backoff is skipped after a timeout: the elapsed time limit already
            # provided the delay, and ASR-A1's total budget must stay well
            # inside 4.5 seconds.
            if not timed_out:
                time.sleep(settings.db_retry_backoff_seconds * attempt)

    assert last_exc is not None
    raise _classify(last_exc) from last_exc


@contextmanager
def session_scope() -> Iterator[Session]:
    """One atomic unit of work - ASR-A4.

    `Availability > Prevent Faults > Transactions`. Every multi-record operation
    runs inside exactly one of these scopes with no intermediate commit, so a
    fault anywhere in the unit rolls back all of it.
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except InjectedTransactionFault as exc:
        session.rollback()
        metrics.increment("transaction_rollbacks_total")
        log_event(
            "transaction_rollback",
            reason="injected_fault",
            error_code="TRANSACTION_FAILED",
        )
        raise TransactionFailedError() from exc
    except DomainError:
        # A rejected business rule rolls its unit of work back, but that is the
        # expected outcome of a 400/404/409 - not a transaction fault, so it does
        # not count towards transaction_rollbacks_total.
        session.rollback()
        raise
    except BaseException as exc:
        session.rollback()
        if not (_is_timeout_error(exc) or _is_unavailable_error(exc)):
            metrics.increment("transaction_rollbacks_total")
            log_event(
                "transaction_rollback",
                reason=type(exc).__name__,
                error_code="TRANSACTION_FAILED",
            )
        raise
    finally:
        session.close()


def check_database_ready() -> bool:
    """Readiness probe: a bounded, cheap round-trip used only by /health/ready."""
    def probe() -> bool:
        with SessionFactory() as session:
            session.execute(text("SELECT 1"))
            return True

    try:
        result = _run_attempt(probe, settings.db_operation_timeout_seconds)
        # Readiness polling doubles as the recovery signal for the health gate.
        health_gate.record_success()
        return result
    except BaseException as exc:  # noqa: BLE001 - readiness never raises
        if _is_unavailable_error(exc):
            health_gate.record_unavailable()
        return False
