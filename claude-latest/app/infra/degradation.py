"""NFR 2.2 - Graceful Degradation, and NFR 2.1 - Exception Detection.

Two cooperating pieces:

``CircuitBreaker``  detects a failing dependency (consecutive system exceptions
                    or timeouts) and trips OPEN, so callers stop paying the
                    latency cost of a dependency that is already known-bad.

``FeatureRegistry`` classifies functionality as CRITICAL or NON_CRITICAL. When a
                    dependency trips, non-critical features are shed while the
                    critical order-workflow path keeps serving.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    """Raised when a call is short-circuited because the breaker is OPEN."""


class CircuitBreaker:
    def __init__(self, name: str, fail_max: int | None = None, reset_timeout: int | None = None):
        self.name = name
        self.fail_max = fail_max or settings.breaker_fail_max
        self.reset_timeout = reset_timeout or settings.breaker_reset_timeout_seconds
        self.state = BreakerState.CLOSED
        self.failures = 0
        self._opened_at = 0.0

    def _record_success(self) -> None:
        self.failures = 0
        self.state = BreakerState.CLOSED

    def _record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.fail_max:
            self.state = BreakerState.OPEN
            self._opened_at = time.monotonic()
            logger.error("circuit %s OPEN after %d failures", self.name, self.failures)

    async def call(
        self, fn: Callable[..., Awaitable[T]], *args: Any, timeout: float | None = None, **kwargs: Any
    ) -> T:
        """Invoke `fn` under breaker supervision and an optional timeout.

        The timeout is the *time-out* half of NFR 2.1: a dependency that never
        answers is converted into a detectable exception instead of hanging.
        """
        if self.state is BreakerState.OPEN:
            if time.monotonic() - self._opened_at < self.reset_timeout:
                raise CircuitOpenError(f"circuit {self.name} is open")
            self.state = BreakerState.HALF_OPEN
            logger.info("circuit %s HALF_OPEN; probing", self.name)

        try:
            coro = fn(*args, **kwargs)
            result = await (asyncio.wait_for(coro, timeout) if timeout else coro)
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result


class Criticality(str, Enum):
    CRITICAL = "CRITICAL"
    NON_CRITICAL = "NON_CRITICAL"


class FeatureRegistry:
    """Decides which features are shed while a dependency is degraded.

    Critical  = the order lifecycle itself (place/accept/invoice/pay/ship/close).
    Non-critical = enrichment that a client can live without: cached read
    acceleration, order-history expansion, analytics counters.
    """

    def __init__(self) -> None:
        self._features: dict[str, Criticality] = {
            "order_workflow": Criticality.CRITICAL,
            "payment_processing": Criticality.CRITICAL,
            "invoice_issuing": Criticality.CRITICAL,
            "cache_acceleration": Criticality.NON_CRITICAL,
            "order_history_expansion": Criticality.NON_CRITICAL,
            "analytics_counters": Criticality.NON_CRITICAL,
        }
        self._shed: set[str] = set()

    def shed(self, feature: str) -> None:
        if self._features.get(feature) is Criticality.CRITICAL:
            raise ValueError(f"refusing to shed critical feature {feature}")
        if feature not in self._shed:
            self._shed.add(feature)
            logger.warning("degraded: shedding non-critical feature %s", feature)

    def restore(self, feature: str) -> None:
        self._shed.discard(feature)

    def is_available(self, feature: str) -> bool:
        return feature not in self._shed

    def status(self) -> dict[str, str]:
        return {
            name: ("SHED" if name in self._shed else "ACTIVE") for name in self._features
        }


cache_breaker = CircuitBreaker("redis-cache")
replica_breaker = CircuitBreaker("postgres-replica")
feature_registry = FeatureRegistry()
