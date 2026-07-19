"""
Circuit breaker for external service calls.
Implements NFR 2.2 (Fault Detection and Recovery).
Tracks metrics: total calls, successes, failures, state transitions.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitBreakerState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by the circuit breaker."""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    open_count: int = 0
    half_open_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


class CircuitBreaker:
    """
    Prevents cascading failures by tripping when failures exceed a threshold.
    After a recovery timeout, transitions to HALF_OPEN to test the service.
    Tracks detailed metrics for observability.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 0,
        recovery_timeout: float = 0.0,
    ) -> None:
        self._name = name
        self._failure_threshold = (
            failure_threshold or settings.circuit_breaker_failure_threshold
        )
        self._recovery_timeout = (
            recovery_timeout or settings.circuit_breaker_recovery_timeout
        )
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()
        self._metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> str:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        return self._metrics

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a call through the circuit breaker."""
        self._metrics.total_calls += 1

        async with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._recovery_timeout_elapsed():
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._metrics.half_open_count += 1
                    logger.info(
                        "CircuitBreaker[%s] transitioning to HALF_OPEN (attempting recovery)",
                        self._name,
                    )
                else:
                    raise RuntimeError(
                        f"CircuitBreaker[{self._name}] is OPEN. "
                        f"Failures: {self._failure_count}/{self._failure_threshold}. "
                        f"Retry in {self._remaining_timeout():.1f}s"
                    )

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                self._metrics.failure_count += 1
                self._metrics.last_failure_time = self._last_failure_time
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitBreakerState.OPEN
                    self._metrics.open_count += 1
                    logger.warning(
                        "CircuitBreaker[%s] TRIPPED to OPEN (failures=%d/%d)",
                        self._name,
                        self._failure_count,
                        self._failure_threshold,
                    )
            raise exc

        # Success — reset if half-open or closed
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                logger.info(
                    "CircuitBreaker[%s] recovered, resetting to CLOSED", self._name
                )
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._metrics.success_count += 1
            self._metrics.last_success_time = time.monotonic()

        return result

    def _recovery_timeout_elapsed(self) -> bool:
        if self._last_failure_time is None:
            return True
        return (time.monotonic() - self._last_failure_time) >= self._recovery_timeout

    def _remaining_timeout(self) -> float:
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self._recovery_timeout - elapsed)
