"""Admission control and deterministic test hooks.

Admission control -- ASR-P2 -- bounds concurrent work on the public product
paths. The defining property is that excess requests are refused *immediately*:
a request that cannot get a slot is answered 429 straight away rather than
waiting for one. That is what separates limiting the event response from
bounding a queue, and the evaluator distinguishes them purely by how long a
rejection takes to arrive.

The observation paths are exempt. Health and metrics are how the system is
watched while it is saturated, so routing them through the very mechanism under
test would make the overload scenario unobservable at the moment it matters.

The test hooks create stimuli without weakening anything. The delay is applied
after admission and while holding the slot, so it produces genuine contention
rather than sidestepping it. The transient-failure hook raises at the database
boundary, inside the retry policy, so the retry being measured is the real one.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .observability import OVERLOAD_REJECTED, log_event, metrics

# Paths that must answer under every condition the scenarios apply.
EXEMPT_PREFIXES = ("/health", "/internal", "/docs", "/redoc", "/openapi.json")

# Per-request fault state. A context variable rather than a global: the
# scenarios drive concurrent traffic, and a shared flag would leak a fault
# injected by one request into another and make the results non-deterministic.
_pending_transient_failures: contextvars.ContextVar[int] = contextvars.ContextVar(
    "pending_transient_failures", default=0
)
_payment_fault: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "payment_fault", default=False
)


def is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)


class AdmissionController:
    """A counting semaphore that refuses rather than blocks when full."""

    def __init__(self, limit: int):
        self.limit = limit
        self._lock = threading.Lock()
        self._in_flight = 0

    def try_acquire(self) -> bool:
        with self._lock:
            if self._in_flight >= self.limit:
                return False
            self._in_flight += 1
            return True

    async def acquire_blocking(self, timeout_s: float) -> bool:
        """Calibration path only: wait for a slot instead of refusing.

        Models the queueing mistake -- the request is still eventually rejected,
        so only the rejection-latency measure reveals the difference.

        The wait is asynchronous so the defect it models is genuinely queueing
        and nothing else. A blocking sleep here would stall the event loop and
        make every request slow, which would fail the scenario for a reason
        unrelated to the tactic and teach the calibration nothing.
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.try_acquire():
                return True
            await asyncio.sleep(0.01)
        return False

    def release(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight


admission = AdmissionController(settings.max_in_flight_requests)


class AdmissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if is_exempt(request.url.path):
            return await call_next(request)

        if settings.defect_queue_instead_of_reject:
            admitted = await admission.acquire_blocking(timeout_s=5.0)
        else:
            admitted = admission.try_acquire()

        if not admitted:
            metrics.increment("requests_rejected_total")
            log_event("overload_rejected", path=request.url.path, code=OVERLOAD_REJECTED)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": OVERLOAD_REJECTED,
                        "message": "too many concurrent requests",
                    }
                },
                headers={"Retry-After": "1"},
            )

        metrics.increment("requests_accepted_total")
        try:
            return await call_next(request)
        finally:
            admission.release()


class TestHookMiddleware(BaseHTTPMiddleware):
    """Reads the test headers and installs per-request fault state.

    Unrecognised or malformed values are ignored in silence, exactly as
    specified: rejecting a bad test header would fail requests for a reason
    that has nothing to do with the behaviour being measured.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        if not settings.enable_test_hooks:
            return await call_next(request)

        _pending_transient_failures.set(0)
        _payment_fault.set(False)

        fault = request.headers.get("X-Test-Fault", "")
        if fault.startswith("transient-db-failures="):
            try:
                count = int(fault.split("=", 1)[1])
                if 0 <= count <= 10:
                    _pending_transient_failures.set(count)
            except ValueError:
                pass  # ignored silently, by contract
        elif fault == "after-payment-update":
            _payment_fault.set(True)

        # The delay runs before the handler, not after it. This middleware sits
        # inside admission control, so sleeping here holds the admitted slot for
        # the full duration -- which is what makes ten slots and a 250 ms delay
        # produce real contention for two hundred callers. Delaying after the
        # response would release the slot first and starve the stimulus.
        #
        # It must be an async sleep. time.sleep blocks the event loop, so no
        # other request can be picked up at all while it runs -- including the
        # ones admission control is supposed to refuse instantly. Rejections
        # then queue behind the delays and arrive seconds late, which reads
        # exactly like the bounded-queue behaviour this tactic is defined
        # against, even though the semaphore itself is correct.
        delay = request.headers.get("X-Test-Delay-Ms")
        if delay and not is_exempt(request.url.path):
            try:
                ms = int(delay)
                if 0 < ms <= 10000:
                    await asyncio.sleep(ms / 1000.0)
            except ValueError:
                pass

        return await call_next(request)


def take_transient_failure() -> bool:
    """Consume one injected failure, if this request has any left."""
    remaining = _pending_transient_failures.get()
    if remaining <= 0:
        return False
    _pending_transient_failures.set(remaining - 1)
    return True


def payment_fault_armed() -> bool:
    return _payment_fault.get()


def clear_fault_state() -> None:
    _pending_transient_failures.set(0)
    _payment_fault.set(False)
