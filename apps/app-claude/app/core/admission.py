"""Admission control - ASR-P2.

`Performance > Control Resource Demand > Manage Work Requests > Limit Event
Response`.

A single counting semaphore bounds concurrently admitted business requests
system-wide. Acquisition is strictly non-blocking: a request that cannot take a
slot is rejected immediately rather than queued, which is what distinguishes
this tactic from a bounded work queue. The middleware wrapping this component
applies it to every public business endpoint; the observation paths are exempt
and never consume a slot.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


class AdmissionController:
    def __init__(self, max_in_flight: int) -> None:
        self._max_in_flight = max_in_flight
        self._lock = threading.Lock()
        self._in_flight = 0
        self._peak_in_flight = 0

    @property
    def max_in_flight(self) -> int:
        return self._max_in_flight

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    @property
    def peak_in_flight(self) -> int:
        with self._lock:
            return self._peak_in_flight

    def _try_acquire(self) -> bool:
        with self._lock:
            if self._in_flight >= self._max_in_flight:
                return False
            self._in_flight += 1
            if self._in_flight > self._peak_in_flight:
                self._peak_in_flight = self._in_flight
            return True

    def _release(self) -> None:
        with self._lock:
            if self._in_flight > 0:
                self._in_flight -= 1

    @contextmanager
    def slot(self) -> Iterator[bool]:
        """Yield True when a slot was admitted, False when it must be rejected.

        Never blocks: the decision is made at once so that excess work receives a
        controlled rejection instead of unbounded waiting.
        """
        admitted = self._try_acquire()
        try:
            yield admitted
        finally:
            if admitted:
                self._release()

    def reset_peak(self) -> None:
        with self._lock:
            self._peak_in_flight = self._in_flight
