"""Counters, controlled errors, and structured logging.

Counters are incremented where the mechanism actually runs -- the cache module
increments hits and misses, the repository increments attempts and reads --
rather than being inferred at the edge. That is what makes them agree with the
database-side scan counts the evaluator compares them against.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

METRIC_NAMES = (
    "cache_hits_total",
    "cache_misses_total",
    "db_product_reads_total",
    "db_product_read_attempts_total",
    "requests_accepted_total",
    "requests_rejected_total",
    "timeouts_total",
    "retry_attempts_total",
    "transaction_rollbacks_total",
)


class Metrics:
    """Monotonic counters, safe under the concurrency the scenarios apply."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values = {name: 0 for name in METRIC_NAMES}

    def increment(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._values[name] += by

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._values)

    def reset(self) -> None:
        with self._lock:
            for name in self._values:
                self._values[name] = 0


metrics = Metrics()


# ── controlled errors ─────────────────────────────────────────────────────

DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
OVERLOAD_REJECTED = "OVERLOAD_REJECTED"
TRANSACTION_FAILED = "TRANSACTION_FAILED"


class ControlledError(HTTPException):
    """A failure the system chose to return, carrying its classification.

    The code is what distinguishes a slow dependency from an absent one. Both
    surface as 503, so without it the timeout and degradation tactics would be
    indistinguishable from outside.
    """

    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message

    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={"error": {"code": self.code, "message": self.message}},
            headers=self.headers,
        )


def validation_error(message: str) -> HTTPException:
    return ControlledError(400, "VALIDATION_FAILED", message)


def not_found(message: str) -> HTTPException:
    return ControlledError(404, "NOT_FOUND", message)


def conflict(message: str) -> HTTPException:
    return ControlledError(409, "WORKFLOW_CONFLICT", message)


# ── structured logging ────────────────────────────────────────────────────


def log_event(event: str, **fields: Any) -> None:
    """One JSON object per line, so a failed scenario is diagnosable from logs.

    Banking account numbers are never logged, so callers pass identifiers only.
    """
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    print(json.dumps(record), file=sys.stdout, flush=True)


def log_startup(settings: Any) -> None:
    """Echo the effective configuration once, as the specification requires."""
    log_event(
        "startup_configuration",
        APP_PORT=settings.app_port,
        MAX_IN_FLIGHT_REQUESTS=settings.max_in_flight_requests,
        DB_OPERATION_TIMEOUT_MS=settings.db_operation_timeout_ms,
        DB_MAX_ATTEMPTS=settings.db_max_attempts,
        DB_RETRY_BACKOFF_MS=settings.db_retry_backoff_ms,
        CACHE_TTL_SECONDS=settings.cache_ttl_seconds,
        ENABLE_TEST_HOOKS=settings.enable_test_hooks,
        active_defects=settings.active_defects(),
    )


class Stopwatch:
    def __enter__(self) -> "Stopwatch":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
