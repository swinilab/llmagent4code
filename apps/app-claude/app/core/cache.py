"""Maintained copies of data - ASR-P1, with the degraded-mode policy of ASR-A3.

`Performance > Manage Resources > Maintain Multiple Copies of Data`.

This is a generic, entity-agnostic component: it knows nothing about Product and
is keyed by opaque strings, so the decision about which entities are served from
a maintained copy lives in the service layer (see architecture/ADRs.md) rather
than being an accident of implementation.

Two properties matter beyond a plain TTL map:

* Single-flight refill. Concurrent misses for the same key do not each issue a
  database read; one loader runs per key while the others wait on the same
  per-key lock and observe the freshly stored entry. This is what bounds
  database reads to roughly one refill per TTL interval under sustained
  concurrent reads.
* Degraded mode. An expired entry is retained rather than discarded, so that
  when the loader fails because the database is unreachable the last known copy
  can still be served. During healthy operation an expired entry is always
  refilled, which preserves the post-TTL freshness ASR-P1 requires.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

from app.core.errors import DependencyUnavailableError
from app.core.logging import log_event
from app.core.metrics import metrics

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    stored_at: float

    def is_fresh(self, ttl_seconds: float, now: float) -> bool:
        return (now - self.stored_at) < ttl_seconds


class TtlCache(Generic[T]):
    """TTL cache with single-flight refill and stale-on-dependency-failure reads."""

    def __init__(self, ttl_seconds: float, name: str = "cache") -> None:
        self._ttl_seconds = ttl_seconds
        self._name = name
        self._entries: dict[str, _Entry[T]] = {}
        self._entry_lock = threading.Lock()
        self._key_locks: dict[str, threading.Lock] = {}
        self._key_locks_guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._key_locks_guard:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock

    def _peek(self, key: str) -> Optional[_Entry[T]]:
        with self._entry_lock:
            return self._entries.get(key)

    def _store(self, key: str, value: T) -> None:
        with self._entry_lock:
            self._entries[key] = _Entry(value=value, stored_at=time.monotonic())

    def get_or_load(self, key: str, loader: Callable[[], T]) -> T:
        """Return the maintained copy, refilling through `loader` when stale.

        `loader` is expected to raise DependencyUnavailableError when the
        database cannot be reached; in that case a retained stale copy is served
        as a degraded read and the failure is not propagated.
        """
        now = time.monotonic()
        entry = self._peek(key)
        if entry is not None and entry.is_fresh(self._ttl_seconds, now):
            metrics.increment("cache_hits_total")
            return entry.value

        lock = self._lock_for(key)
        with lock:
            # Re-check under the per-key lock: a concurrent refill may have
            # completed while this caller was waiting, in which case it must be
            # served as a hit rather than issuing a second database read.
            now = time.monotonic()
            entry = self._peek(key)
            if entry is not None and entry.is_fresh(self._ttl_seconds, now):
                metrics.increment("cache_hits_total")
                return entry.value

            metrics.increment("cache_misses_total")
            try:
                value = loader()
            except DependencyUnavailableError:
                stale = self._peek(key)
                if stale is not None:
                    log_event(
                        "degraded_read_served",
                        cache=self._name,
                        key=key,
                        age_seconds=round(time.monotonic() - stale.stored_at, 3),
                        error_code="DEPENDENCY_UNAVAILABLE",
                        degraded=True,
                    )
                    return stale.value
                raise
            self._store(key, value)
            return value

    def invalidate(self, key: str) -> None:
        with self._entry_lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._entry_lock:
            self._entries.clear()
        with self._key_locks_guard:
            self._key_locks.clear()

    def peek_value(self, key: str) -> Optional[Any]:
        entry = self._peek(key)
        return None if entry is None else entry.value
