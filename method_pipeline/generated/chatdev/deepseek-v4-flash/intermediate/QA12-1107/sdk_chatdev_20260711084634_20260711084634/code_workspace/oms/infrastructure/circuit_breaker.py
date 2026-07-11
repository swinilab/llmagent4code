"""
Circuit breaker pattern implementation (NFR 2.1 Graceful Degradation).

The circuit breaker wraps calls to non-critical features. When failures
exceed a threshold, the circuit "opens" and subsequent calls fail fast
(returning a fallback) instead of waiting. After a recovery timeout, the
circuit transitions to "half-open" to probe for recovery.

This is used to protect the core checkout flow from failures in
non-essential features (e.g., product recommendations, analytics).
"""
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"          # Normal operation
    OPEN = "OPEN"              # Failing fast
    HALF_OPEN = "HALF_OPEN"    # Probing for recovery


class CircuitBreaker:
    """Circuit breaker for a single operation.

    Args:
        name: Human-readable name for logging.
        failure_threshold: Number of consecutive failures to open the circuit.
        recovery_timeout: Seconds to wait before transitioning to half-open.
        fallback: Optional callable returning a default value on open circuit.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        fallback: Optional[Callable[..., T]] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute the protected function with circuit breaker logic."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    logger.info("Circuit %s transitioning to HALF_OPEN", self.name)
                    self._state = CircuitState.HALF_OPEN
                else:
                    logger.warning("Circuit %s is OPEN — failing fast", self.name)
                    if self.fallback:
                        return self.fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError(self.name)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except Exception as exc:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self.failure_threshold:
                    logger.error(
                        "Circuit %s OPEN after %d failures",
                        self.name, self._failure_count,
                    )
                    self._state = CircuitState.OPEN
                if self._state == CircuitState.HALF_OPEN:
                    logger.info("Circuit %s back to OPEN (probe failed)", self.name)
                    self._state = CircuitState.OPEN
            if self.fallback:
                return self.fallback(*args, **kwargs)
            raise

        # Success
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit %s CLOSED (probe succeeded)", self.name)
                self._state = CircuitState.CLOSED
            self._failure_count = 0

        return result

    def reset(self) -> None:
        """Manually reset the circuit to closed."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str):
        self.circuit_name = name
        super().__init__(f"Circuit breaker '{name}' is open — call rejected")


# ---------------------------------------------------------------------------
# Registry of circuit breakers for different features
# ---------------------------------------------------------------------------
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name)
    return _circuit_breakers[name]


def get_all_circuit_states() -> dict[str, str]:
    """Return the state of all registered circuit breakers (for health endpoint)."""
    return {name: cb.state.value for name, cb in _circuit_breakers.items()}
