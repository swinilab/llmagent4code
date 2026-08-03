"""In-process counters backing GET /internal/metrics.

Every counter is incremented at the exact site where its mechanism executes; no
counter is derived, estimated, or written by a test hook. The lock keeps
increments consistent under the concurrency ASR-P1 and ASR-P2 exercise.
"""

from __future__ import annotations

import threading

COUNTER_NAMES: tuple[str, ...] = (
    "cache_hits_total",
    "cache_misses_total",
    "db_product_reads_total",
    "db_product_read_attempts_total",
    "requests_accepted_total",
    "requests_rejected_total",
    "timeouts_total",
    "retry_attempts_total",
    "transaction_rollbacks_total",
)


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, int] = {name: 0 for name in COUNTER_NAMES}

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._values[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._values)

    def reset(self) -> None:
        with self._lock:
            for name in COUNTER_NAMES:
                self._values[name] = 0


metrics = Metrics()
