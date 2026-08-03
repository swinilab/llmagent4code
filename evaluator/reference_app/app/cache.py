"""Maintained copies of product data -- ASR-P1 and, in degraded form, ASR-A3.

Two requirements pull in opposite directions and both must hold at once:

  ASR-P1 wants the copy to expire. After the TTL, a read must reflect a change
  made directly in PostgreSQL, so the database stays authoritative.

  ASR-A3 wants the copy to survive a sixty-second outage, which is twelve times
  the five-second TTL.

They are reconciled by giving each entry two lifetimes rather than one. The TTL
governs freshness during normal operation; a separate, much longer horizon
governs how long a known-stale copy may still be served *when the database is
unreachable*. An entry past its TTL is refreshed if the database answers, and
served stale only if it does not. Simply lengthening the TTL would satisfy the
outage and fail the staleness probe.

The single-flight lock is the other load-bearing detail. Fifty concurrent
readers arriving at an expired entry must produce one database read between
them, not fifty; without it the read budget is exhausted on the first refill.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from .config import settings
from .observability import log_event, metrics

T = TypeVar("T")

# How long a stale copy may still answer while the database is unreachable.
# Comfortably longer than the outage the scenario applies, so the degraded path
# is limited by the policy rather than by an arbitrary expiry landing mid-test.
DEGRADED_HORIZON_SECONDS = 600


@dataclass
class Entry(Generic[T]):
    value: T
    stored_at: float

    def age(self) -> float:
        return time.monotonic() - self.stored_at

    def is_fresh(self, ttl: float) -> bool:
        return self.age() < ttl

    def is_servable_when_degraded(self) -> bool:
        return self.age() < DEGRADED_HORIZON_SECONDS


class DependencyUnavailable(RuntimeError):
    """The loader could not reach the database at all."""


class ProductCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._entries: dict[str, Entry[Any]] = {}
        self._entry_lock = threading.Lock()
        # One lock per key: concurrent readers of the same product serialise on
        # the refill, while readers of different products do not block.
        self._refill_locks: dict[str, threading.Lock] = {}
        self._refill_locks_guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._refill_locks_guard:
            return self._refill_locks.setdefault(key, threading.Lock())

    def _peek(self, key: str) -> Entry[Any] | None:
        with self._entry_lock:
            return self._entries.get(key)

    def _store(self, key: str, value: Any) -> None:
        with self._entry_lock:
            self._entries[key] = Entry(value, time.monotonic())

    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        """Return the product, refreshing from `loader` when the copy is stale.

        `loader` raises DependencyUnavailable when the database cannot be
        reached, which is the signal to fall back to a stale copy rather than
        to fail.
        """
        entry = self._peek(key)
        if entry is not None and entry.is_fresh(self.ttl):
            metrics.increment("cache_hits_total")
            return entry.value

        if settings.defect_no_single_flight:
            # Calibration path: every concurrent miss loads independently.
            return self._load_and_store(key, loader, entry)

        lock = self._lock_for(key)
        with lock:
            # Re-check under the lock: whoever held it may have just refilled,
            # in which case the waiters are hits and issue no read of their own.
            entry = self._peek(key)
            if entry is not None and entry.is_fresh(self.ttl):
                metrics.increment("cache_hits_total")
                return entry.value
            return self._load_and_store(key, loader, entry)

    def _load_and_store(self, key: str, loader: Callable[[], Any], stale: Entry[Any] | None) -> Any:
        metrics.increment("cache_misses_total")
        try:
            value = loader()
        except DependencyUnavailable:
            # Degraded operation: a known copy is better than an error, but only
            # one that exists. Nothing is invented for a key never loaded.
            if stale is None:
                raise
            if settings.defect_no_degraded_cache:
                raise
            if not stale.is_servable_when_degraded():
                raise
            log_event("degraded_read", key=key, stale_age_s=round(stale.age(), 2))
            return stale.value

        self._store(key, value)
        return value

    def invalidate(self, key: str) -> None:
        with self._entry_lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._entry_lock:
            self._entries.clear()
        with self._refill_locks_guard:
            self._refill_locks.clear()


product_cache = ProductCache(settings.cache_ttl_seconds)
