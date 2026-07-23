"""
Circuit Breaker pattern (Resilience4j-style) for non-essential service calls.

States: CLOSED (normal), OPEN (failing), HALF_OPEN (probing recovery).

When OPEN, calls fail fast with a fallback response.
After open_duration_ms, transitions to HALF_OPEN.
In HALF_OPEN, if success_threshold consecutive calls succeed, back to CLOSED;
  if any fails, back to OPEN.

Used for non-essential features (NFR 2.1):
  - Personalized recommendations
  - Heavy analytics logging
  - External shipping rate quotes

Includes a configurable timeout on the protected function call to prevent
hanging requests from keeping the circuit closed (NFR 2.1).

Supports Redis-backed state for shared circuit breaker state across workers.
When Redis is available, the circuit breaker state is stored in Redis so that
all workers see the same state. When Redis is unavailable, falls back to
in-memory per-worker state.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

from oms.config import settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Per-service circuit breaker with configurable thresholds and timeout.

    Fallback is passed as a parameter to call() rather than stored as instance
    state, to avoid race conditions when multiple concurrent requests set
    different fallbacks on the same shared instance.

    The timeout parameter (default 5s) ensures that if the downstream call
    hangs, the circuit breaker will open rather than accumulating pending
    requests (NFR 2.1).

    Supports Redis-backed state for shared state across workers. When Redis
    is configured, the circuit state, failure count, and success count are
    stored in Redis with atomic operations.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        open_duration_ms: int = 30000,
        timeout_seconds: float = 5.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.open_duration_ms = open_duration_ms
        self.timeout_seconds = timeout_seconds

        # In-memory state (fallback)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_open_time: float = 0.0
        self._lock = asyncio.Lock()

        # Redis client (set externally)
        self._redis_client = None

    def set_redis_client(self, client):
        """Set the Redis client for shared-state mode."""
        self._redis_client = client

    def _redis_key(self, suffix: str) -> str:
        return f"circuit_breaker:{self.name}:{suffix}"

    @property
    def state(self) -> CircuitState:
        return self._state

    async def _load_state_from_redis(self):
        """Load circuit breaker state from Redis."""
        try:
            state_raw = await self._redis_client.get(self._redis_key("state"))
            if state_raw:
                self._state = CircuitState(state_raw)
            failure_count_raw = await self._redis_client.get(self._redis_key("failure_count"))
            if failure_count_raw:
                self._failure_count = int(failure_count_raw)
            success_count_raw = await self._redis_client.get(self._redis_key("success_count"))
            if success_count_raw:
                self._success_count = int(success_count_raw)
            last_open_raw = await self._redis_client.get(self._redis_key("last_open_time"))
            if last_open_raw:
                self._last_open_time = float(last_open_raw)
        except Exception as e:
            logger.warning("Failed to load circuit breaker state from Redis: %s", e)

    async def _save_state_to_redis(self):
        """Save circuit breaker state to Redis."""
        try:
            pipe = self._redis_client.pipeline()
            pipe.set(self._redis_key("state"), self._state.value)
            pipe.set(self._redis_key("failure_count"), self._failure_count)
            pipe.set(self._redis_key("success_count"), self._success_count)
            pipe.set(self._redis_key("last_open_time"), self._last_open_time)
            await pipe.execute()
        except Exception as e:
            logger.warning("Failed to save circuit breaker state to Redis: %s", e)

    async def call(self, func: Callable, *args, fallback: Optional[Callable] = None, **kwargs) -> Any:
        """Execute func with circuit breaker protection and timeout.

        Args:
            func: The async function to call.
            fallback: Optional async function to call when circuit is OPEN.
                      Passed per-call to avoid race conditions on shared state.
        """
        # Load state from Redis if available
        if self._redis_client is not None:
            await self._load_state_from_redis()

        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._is_open_timeout_expired():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    return await self._get_fallback(fallback)

            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0

        try:
            # Apply timeout to prevent hanging calls from keeping circuit closed
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_seconds,
            )
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._success_count += 1
                    if self._success_count >= self.success_threshold:
                        self._state = CircuitState.CLOSED
                        self._failure_count = 0
                        self._success_count = 0
                elif self._state == CircuitState.CLOSED:
                    self._failure_count = 0  # reset on success
            # Save state to Redis if available
            if self._redis_client is not None:
                await self._save_state_to_redis()
            return result
        except Exception as e:
            async with self._lock:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_open_time = time.monotonic()
                    self._success_count = 0
            # Save state to Redis if available
            if self._redis_client is not None:
                await self._save_state_to_redis()
            return await self._get_fallback(fallback)

    def _is_open_timeout_expired(self) -> bool:
        return (time.monotonic() - self._last_open_time) * 1000 >= self.open_duration_ms

    async def _get_fallback(self, fallback: Optional[Callable] = None) -> Any:
        if fallback:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback()
            return fallback()
        return None

    def get_metrics(self) -> dict:
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }


# Registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=settings.cb_failure_threshold,
            success_threshold=settings.cb_success_threshold,
            open_duration_ms=settings.cb_open_duration_ms,
            timeout_seconds=5.0,
        )
    return _circuit_breakers[name]


def get_all_circuit_breaker_metrics() -> list[dict]:
    return [cb.get_metrics() for cb in _circuit_breakers.values()]


def wire_circuit_breakers_to_redis(redis_client):
    """Wire all existing circuit breakers to use Redis for shared state."""
    for cb in _circuit_breakers.values():
        cb.set_redis_client(redis_client)
