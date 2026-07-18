"""
Circuit breaker for fault detection and automatic recovery (NFR 2.2).

When a downstream operation fails repeatedly, the circuit opens and
short-circuits subsequent calls. After a cooldown, the breaker enters
half-open state and allows a limited number of probe calls. If they
succeed, the circuit closes; if they fail, it re-opens.
"""
import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from oms.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and rejects a call."""
    pass


class CircuitBreaker:
    """
    Async circuit breaker implementing the three-state pattern.

    Parameters are sourced from application settings but can be overridden
    per instance for testing.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
        half_open_max_calls: int | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold or settings.cb_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.cb_recovery_timeout
        self.half_open_max_calls = half_open_max_calls or settings.cb_half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current breaker state (computed lazily for OPEN→HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit '%s' transitioning OPEN → HALF_OPEN", self.name)
        return self._state

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """
        Execute *func* through the breaker. Raises CircuitBreakerOpenError
        if the circuit is open, or propagates any exception from *func*
        while recording failures.
        """
        async with self._lock:
            current = self.state
            if current == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN — rejecting call"
                )
            if current == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is HALF_OPEN and at max probe calls"
                )
            if current == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            await self._on_failure()
            raise exc

        await self._on_success()
        return result

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit '%s' HALF_OPEN → CLOSED (recovered)", self.name)
            else:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit '%s' HALF_OPEN → OPEN (probe failed)", self.name)
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' CLOSED → OPEN (failures=%d >= threshold=%d)",
                    self.name, self._failure_count, self.failure_threshold,
                )

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED (for testing)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

    def status(self) -> dict:
        """Return a status dict for health-check endpoints."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }


class CircuitBreakerRegistry:
    """Central registry so health checks can inspect all breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name)
        return self._breakers[name]

    def all_status(self) -> list[dict]:
        return [b.status() for b in self._breakers.values()]


circuit_breaker_registry = CircuitBreakerRegistry()


def with_circuit_breaker(name: str) -> Callable:
    """
    Decorator that wraps an async function with a named circuit breaker.

    Usage::

        @with_circuit_breaker("payment_gateway")
        async def call_gateway(): ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        breaker = circuit_breaker_registry.get_or_create(name)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator