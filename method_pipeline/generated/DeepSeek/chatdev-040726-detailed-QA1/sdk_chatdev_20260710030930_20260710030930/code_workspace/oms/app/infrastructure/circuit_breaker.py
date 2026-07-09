"""Circuit breaker for downstream dependency resilience (NFR 1.3).

Pattern: Resilience4j-style circuit breaker
  - States: CLOSED (normal), OPEN (failing), HALF_OPEN (probing)
  - Failure rate threshold: 50% over a sliding window
  - Open duration: 30 seconds before transitioning to HALF_OPEN
  - Half-open trial count: 3 successful calls to transition back to CLOSED

This wraps calls to external downstream dependencies (e.g., payment gateway,
shipping API). For this implementation, we simulate the pattern; in production,
a library like pybreaker or aiobreaker would be used.
"""

import time
from collections import deque
from enum import Enum
from typing import Any, Callable, Optional

from app.config import settings


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""
    pass


class CircuitBreaker:
    """Sliding-window circuit breaker for async callables.

    Uses a deque-based sliding window of the last N calls to compute
    the failure rate.
    """

    def __init__(
        self,
        name: str,
        failure_rate_threshold: float = settings.cb_failure_rate_threshold,
        open_duration_seconds: int = settings.cb_open_duration_seconds,
        half_open_trial_count: int = settings.cb_half_open_trial_count,
        window_size: int = 100,
    ) -> None:
        self.name = name
        self._failure_rate_threshold = failure_rate_threshold
        self._open_duration = open_duration_seconds
        self._half_open_trial_count = half_open_trial_count
        self._window_size = window_size

        self._state = CircuitState.CLOSED
        self._last_open_time: Optional[float] = None
        self._half_open_successes = 0
        self._sliding_window: deque[bool] = deque(maxlen=window_size)  # True=success, False=failure

    @property
    def state(self) -> CircuitState:
        """Get current state, transitioning OPEN→HALF_OPEN if duration elapsed."""
        if self._state == CircuitState.OPEN and self._last_open_time is not None:
            if time.monotonic() - self._last_open_time >= self._open_duration:
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0
        return self._state

    def _record_outcome(self, success: bool) -> None:
        """Record a call outcome in the sliding window."""
        self._sliding_window.append(success)
        # Recalculate failure rate
        if len(self._sliding_window) >= self._window_size:
            failures = sum(1 for s in self._sliding_window if not s)
            rate = (failures / len(self._sliding_window)) * 100.0
            if rate >= self._failure_rate_threshold and self._state == CircuitState.CLOSED:
                self._state = CircuitState.OPEN
                self._last_open_time = time.monotonic()

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a callable through the circuit breaker.

        Args:
            func: Async callable to execute.
            *args, **kwargs: Arguments to pass to the callable.

        Returns:
            The result of the callable.

        Raises:
            CircuitBreakerOpenError: If the circuit is OPEN.
            Any exception from the wrapped callable.
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN. Request rejected."
            )

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_successes >= self._half_open_trial_count:
                # Enough successful probes, close the circuit
                self._state = CircuitState.CLOSED
                self._half_open_successes = 0
            else:
                # Allow the call as a probe
                pass

        try:
            result = await func(*args, **kwargs)
            self._record_outcome(success=True)
            if current_state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
            return result
        except Exception:
            self._record_outcome(success=False)
            if current_state == CircuitState.HALF_OPEN:
                # Probe failed, back to OPEN
                self._state = CircuitState.OPEN
                self._last_open_time = time.monotonic()
            raise


# Singleton circuit breakers for downstream dependencies
payment_gateway_cb = CircuitBreaker(name="payment_gateway")
shipping_api_cb = CircuitBreaker(name="shipping_api")
