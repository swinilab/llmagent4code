"""Cross-cutting request middleware: admission control and test-hook context.

This is the single place admission control is applied, so it governs every
public business endpoint rather than any one route (ASR-P2). The observation
paths are the sole exemption: they bypass admission entirely, never consume a
slot, and are never delayed by X-Test-Delay-Ms, so the system stays observable
while it is overloaded or its database is unreachable.
"""

from __future__ import annotations

import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.admission import AdmissionController
from app.core.config import settings
from app.core.errors import OVERLOAD_REJECTED, error_body
from app.core.logging import log_event
from app.core.metrics import metrics
from app.core.test_hooks import parse_delay_ms, parse_fault, reset_current_fault, set_current_fault

# Observation infrastructure, not business traffic.
EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/health/live",
        "/health/ready",
        "/internal/metrics",
        "/internal/admission",
        "/internal/test/reset",
    }
)

# Documentation endpoints are static and must not consume admitted slots either.
EXEMPT_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/openapi.json")

RETRY_AFTER_SECONDS = "1"

admission_controller = AdmissionController(settings.max_in_flight_requests)


def is_exempt(path: str) -> bool:
    if path in EXEMPT_PATHS:
        return True
    return any(path == prefix or path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


class AdmissionControlMiddleware(BaseHTTPMiddleware):
    """Bounds concurrently admitted business requests system-wide.

    Rejection is immediate - a request that cannot take a slot is refused at once
    and never waits in a queue - which is what makes this Limit Event Response
    rather than a bounded work queue.
    """

    async def dispatch(self, request: Request, call_next):
        if is_exempt(request.url.path):
            return await call_next(request)

        with admission_controller.slot() as admitted:
            if not admitted:
                metrics.increment("requests_rejected_total")
                log_event(
                    "overload_rejected",
                    path=request.url.path,
                    method=request.method,
                    max_in_flight=admission_controller.max_in_flight,
                    error_code=OVERLOAD_REJECTED,
                )
                return JSONResponse(
                    status_code=429,
                    content=error_body(
                        OVERLOAD_REJECTED,
                        "The in-flight request limit was reached; retry shortly.",
                    ),
                    headers={"Retry-After": RETRY_AFTER_SECONDS},
                )

            metrics.increment("requests_accepted_total")
            return await call_next(request)


class TestHookMiddleware(BaseHTTPMiddleware):
    """Binds the per-request injected-fault directive and applies the test delay.

    The delay runs *after* admission and while the slot is held, so an overload
    client can exercise the real admission policy. Both headers are ignored
    entirely when ENABLE_TEST_HOOKS=false, and a malformed value is ignored
    silently rather than failing the request.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_test_hooks or is_exempt(request.url.path):
            return await call_next(request)

        fault = parse_fault(request.headers.get("X-Test-Fault"))
        token = set_current_fault(fault)
        try:
            delay_ms = parse_delay_ms(request.headers.get("X-Test-Delay-Ms"))
            if delay_ms > 0:
                # Awaited, not blocking: the request keeps holding its admitted
                # slot for the full delay, but the event loop stays free to
                # dispatch further requests. A blocking sleep here would stall
                # the loop and delay the *rejections* too, which would violate
                # the immediate-rejection requirement of ASR-P2.
                await asyncio.sleep(delay_ms / 1000.0)
            return await call_next(request)
        finally:
            reset_current_fault(token)
