"""
Async-compatible Circuit Breaker for non-essential service calls (NFR 2.1).

Replaces the synchronous `circuitbreaker` library which does NOT support
`async def` functions. Uses a custom `AsyncCircuitBreaker` with asyncio.Lock
for thread-safe state transitions.

States: CLOSED (normal) → OPEN (failures exceed threshold) → HALF_OPEN (probing)

Reliability/Latency tension: ~0.01ms overhead in CLOSED state (atomic read).
When OPEN, saves 5s (the HTTP timeout) per call. Under extreme load, prevents
cascading failures by failing fast — core checkout is never blocked.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class RecommendationServiceError(Exception):
    """Raised when the recommendation service is unavailable."""


class AsyncCircuitBreaker:
    """
    Async-compatible circuit breaker for non-essential service calls (NFR 2.1).

    Thread-safe via asyncio.Lock. State machine:
      CLOSED  → normal operation, calls pass through
      OPEN    → failures >= threshold, calls fast-fail
      HALF_OPEN → after recovery_timeout, single probe call allowed
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state: str = "CLOSED"
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncCircuitBreaker":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        if exc_type is None:
            # Success — reset failure count, close if half-open
            async with self._lock:
                self._failure_count = 0
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    logger.info(
                        "Circuit breaker '%s' closed after successful probe",
                        self._name,
                    )
            return False

        if isinstance(exc_val, RecommendationServiceError):
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self._failure_threshold:
                    self._state = "OPEN"
                    logger.warning(
                        "Circuit breaker '%s' OPEN (failures=%d/%d)",
                        self._name,
                        self._failure_count,
                        self._failure_threshold,
                    )
            return False

        # Re-raise unexpected exceptions
        return False

    async def call(self, func, *args: Any, **kwargs: Any) -> Any:
        """Execute a call through the circuit breaker."""
        async with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = "HALF_OPEN"
                    logger.info(
                        "Circuit breaker '%s' HALF_OPEN (probing)", self._name
                    )
                else:
                    raise RecommendationServiceError(
                        f"Circuit breaker '{self._name}' is OPEN"
                    )

        try:
            async with self:
                return await func(*args, **kwargs)
        except RecommendationServiceError:
            raise


# Singleton instance configured from settings
_recommendation_cb = AsyncCircuitBreaker(
    name="recommendation",
    failure_threshold=settings.CB_FAILURE_THRESHOLD,
    recovery_timeout=settings.CB_RECOVERY_TIMEOUT,
)


async def fetch_recommendations(customer_id: str) -> dict[str, Any]:
    """Call the external recommendation service through the circuit breaker."""

    async def _do_fetch() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.RECOMMENDATION_URL}?customer_id={customer_id}"
            )
            if response.status_code != 200:
                raise RecommendationServiceError(
                    f"Recommendation service returned {response.status_code}"
                )
            return response.json()

    return await _recommendation_cb.call(_do_fetch)


async def get_recommendations_with_fallback(customer_id: str) -> dict[str, Any]:
    """
    Fetch recommendations with circuit-breaker protection and fallback.

    When the circuit breaker is open or the service is unreachable, returns
    an empty recommendation list with a 'fallback: true' flag. This ensures
    core checkout functionality is never blocked (NFR 2.1).
    """
    try:
        result = await fetch_recommendations(customer_id)
        logger.info("Recommendations fetched successfully for customer %s", customer_id)
        return result
    except RecommendationServiceError:
        logger.warning(
            "Recommendation circuit breaker open or service unavailable for customer %s. "
            "Returning fallback (empty recommendations).",
            customer_id,
        )
        return {"recommendations": [], "fallback": True}
