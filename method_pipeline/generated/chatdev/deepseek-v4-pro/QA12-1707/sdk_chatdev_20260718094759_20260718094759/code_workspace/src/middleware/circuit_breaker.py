"""
Circuit breaker for graceful degradation (NFR 2.1, 2.2).

ADR-007: Decorator-based circuit breaker with half-open recovery.
  Decision: In-process circuit breaker tracking failure counts per operation.
  Context: NFR 2.1 (Graceful Degradation) — non-essential features degrade under load;
    NFR 2.2 (Fault Detection) — automatic recovery attempts.
  Alternatives: (a) Hystrix/pybreaker library — external dependency;
    (b) envoy sidecar — overkill for single-node.
  Consequences: In-process state lost on restart; acceptable given NFR 2.3 handles
    state preservation at the database layer.
"""

from __future__ import annotations

import functools
import time
from collections import defaultdict
from enum import Enum, auto
from typing import Any, Callable

from src.config import settings


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """Tracks failure counts and trips the circuit when threshold exceeded."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.circuit_breaker_recovery_timeout_seconds
        self._states: dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self._failure_counts: dict[str, int] = defaultdict(int)
        self._last_failure: dict[str, float] = defaultdict(float)

    def _transition(self, name: str) -> CircuitState:
        """Determine current state and auto-transition."""
        state = self._states[name]
        if state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure[name] >= self.recovery_timeout:
                self._states[name] = CircuitState.HALF_OPEN
                self._failure_counts[name] = 0
                return CircuitState.HALF_OPEN
            return CircuitState.OPEN
        return state

    def allow(self, name: str) -> bool:
        """Return True if the operation is allowed to proceed."""
        state = self._transition(name)
        return state != CircuitState.OPEN

    def record_success(self, name: str) -> None:
        """Reset failure count on success."""
        self._failure_counts[name] = 0
        self._states[name] = CircuitState.CLOSED

    def record_failure(self, name: str) -> None:
        """Increment failure count; trip if threshold exceeded."""
        self._failure_counts[name] += 1
        self._last_failure[name] = time.monotonic()
        if self._failure_counts[name] >= self.failure_threshold:
            self._states[name] = CircuitState.OPEN


_global_cb = CircuitBreaker()


def circuit_breaker(name: str | None = None):
    """Decorator that wraps a function with circuit breaker logic."""

    def decorator(func: Callable) -> Callable:
        cb_name = name or func.__qualname__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _global_cb.allow(cb_name):
                from src.utils.exceptions import ServiceUnavailableError

                raise ServiceUnavailableError(
                    f"Circuit breaker open for {cb_name}"
                )
            try:
                result = await func(*args, **kwargs)
                _global_cb.record_success(cb_name)
                return result
            except Exception:
                _global_cb.record_failure(cb_name)
                raise

        return wrapper

    return decorator
