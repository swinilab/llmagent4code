"""Deterministic test hooks, active only when ENABLE_TEST_HOOKS=true.

The hooks create stimuli for the ASR scenarios. They deliberately do not bypass
any mechanism: the transient-failure hook raises at the real database-read
boundary so the genuine retry policy observes it, and the payment hook raises
inside the real transaction so the genuine rollback occurs.

Header parsing is intentionally lenient. An unrecognized, malformed, or
out-of-range value is ignored silently and the request proceeds as if the header
were absent - a bad test header never turns into a 400.
"""

from __future__ import annotations

import threading
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

TRANSIENT_DB_FAILURES = "transient-db-failures"
AFTER_PAYMENT_UPDATE = "after-payment-update"

MAX_DELAY_MS = 60_000
MAX_TRANSIENT_FAILURES = 100


@dataclass
class RequestFault:
    """The single directive carried by X-Test-Fault for one request."""

    name: str
    remaining: int = 0


_current_fault: ContextVar[Optional[RequestFault]] = ContextVar("current_fault", default=None)


class InjectedTransientDbError(Exception):
    """A transient database-boundary fault, classified as retryable."""


class InjectedTransactionFault(Exception):
    """Raised inside the payment-verification transaction, before commit."""


class TestHookState:
    """Tracks injected-fault state so POST /internal/test/reset can clear it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0

    def register(self) -> None:
        with self._lock:
            self._active += 1

    def reset(self) -> None:
        with self._lock:
            self._active = 0

    @property
    def active(self) -> int:
        with self._lock:
            return self._active


hook_state = TestHookState()


def parse_delay_ms(raw: Optional[str]) -> int:
    """Parse X-Test-Delay-Ms; silently yield 0 for anything unusable."""
    if not settings.enable_test_hooks or raw is None:
        return 0
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        return 0
    if value < 0 or value > MAX_DELAY_MS:
        return 0
    return value


def parse_fault(raw: Optional[str]) -> Optional[RequestFault]:
    """Parse the single X-Test-Fault directive; ignore anything unrecognized.

    Exactly one directive per request is supported by contract - no
    comma-separated or repeated-header composition.
    """
    if not settings.enable_test_hooks or raw is None:
        return None
    directive = raw.strip()
    if not directive:
        return None

    if directive == AFTER_PAYMENT_UPDATE:
        return RequestFault(name=AFTER_PAYMENT_UPDATE)

    if directive.startswith(f"{TRANSIENT_DB_FAILURES}="):
        _, _, count_raw = directive.partition("=")
        try:
            count = int(count_raw.strip())
        except ValueError:
            return None
        if count < 0 or count > MAX_TRANSIENT_FAILURES:
            return None
        return RequestFault(name=TRANSIENT_DB_FAILURES, remaining=count)

    return None


def set_current_fault(fault: Optional[RequestFault]):
    if fault is not None:
        hook_state.register()
    return _current_fault.set(fault)


def reset_current_fault(token) -> None:
    _current_fault.reset(token)


def current_fault() -> Optional[RequestFault]:
    if not settings.enable_test_hooks:
        return None
    return _current_fault.get()


def consume_transient_db_failure() -> bool:
    """Consume one injected transient failure at the Product read boundary.

    Returns True when this attempt must fail transiently. Decrementing here -
    rather than at the HTTP layer - is what makes the genuine retry policy the
    thing being exercised.
    """
    fault = current_fault()
    if fault is None or fault.name != TRANSIENT_DB_FAILURES:
        return False
    if fault.remaining <= 0:
        return False
    fault.remaining -= 1
    return True


def should_fault_after_payment_update() -> bool:
    fault = current_fault()
    return fault is not None and fault.name == AFTER_PAYMENT_UPDATE
