"""
Circuit Breaker implementation (NFR 2.1 – Graceful Degradation).

Three states: CLOSED (normal), OPEN (failures exceed threshold), HALF_OPEN (probing).
When OPEN, calls are rejected immediately with a fallback response.
After recovery_timeout, transitions to HALF_OPEN where a limited number of
probe calls are allowed. If they succeed, the breaker closes; otherwise it
re-opens.
"""
import enum
import logging
import time
from threading import Lock
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Thread-safe circuit breaker with configurable thresholds.

    Usage:
        cb = CircuitBreaker("my.service", failure_threshold=5, recovery_timeout=30)
        result = cb.call(my_function, arg1, arg2)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._lock = Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    def call(
        self,
        func: Callable[..., T],
        fallback: Optional[Callable[..., T]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute *func* if the circuit is closed or half-open.
        If the circuit is open, call *fallback* (or raise CircuitBreakerOpenError).
        """
        if self._try_acquire():
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as exc:
                self._on_failure()
                if fallback is not None:
                    logger.warning(
                        "Circuit '%s' – primary call failed, using fallback", self.name
                    )
                    return fallback(*args, **kwargs)
                raise
        else:
            # Circuit is open
            if fallback is not None:
                logger.info("Circuit '%s' is OPEN – using fallback", self.name)
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpenError(self.name, self._state)

    def _try_acquire(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self._last_failure_time is None:
                    return False
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info(
                        "Circuit '%s' transitioning OPEN -> HALF_OPEN", self.name
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    return True
                return False
            # HALF_OPEN – allow limited probe calls
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def _on_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "Circuit '%s' HALF_OPEN probe succeeded -> CLOSED", self.name
                )
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._last_failure_time = None
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self.failure_threshold
            ):
                logger.warning(
                    "Circuit '%s' CLOSED -> OPEN (failures=%d)",
                    self.name, self._failure_count,
                )
                self._state = CircuitState.OPEN
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "Circuit '%s' HALF_OPEN probe failed -> OPEN", self.name
                )
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str, state: CircuitState):
        super().__init__(f"Circuit '{name}' is {state.value} – call rejected")
        self.circuit_name = name
        self.circuit_state = state
