"""
Retry configuration with exponential backoff for transient failures (NFR 2.2).

Uses the `tenacity` library. Applied to database operations that may fail
due to temporary connection drops or deadlocks.

Reliability/Latency tension: Retries add latency proportional to
max_attempts * max_wait. With 3 attempts and 5s max wait, worst-case
retry adds ~7.5s to checkout. This is acceptable because:
1. Transient DB failures are rare (<0.1% of requests).
2. The alternative (returning 500 to the user) is worse for both
   reliability and user experience.
3. The circuit breaker on non-essential calls prevents cascading failures.

Session safety: Before each retry, the decorator attempts to roll back the
SQLAlchemy session to a clean state. This prevents "nested transaction"
errors when a flush() fails mid-transaction and the session is left in a
partial state (see NFR 2.2 — Fault Detection and Recovery).
"""
from __future__ import annotations

import logging
from typing import Any, TypeVar

from sqlalchemy.exc import DBAPIError
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _rollback_session_before_retry(retry_state: Any) -> None:
    """
    Before each retry attempt, roll back the session if it exists.

    This is critical because a failed flush() leaves the session in a
    partial state where subsequent operations fail with "nested transaction"
    errors. By rolling back, we give the next attempt a clean session.

    The retry_state contains the function's positional args; the first
    arg is typically `self` (the repository instance), which has a
    `_session` attribute.
    """
    if not retry_state.args:
        return
    self_arg = retry_state.args[0]
    session = getattr(self_arg, "_session", None)
    if session is not None:
        try:
            if session.is_active:
                session.rollback()
                logger.debug("Session rolled back before retry attempt %d", retry_state.attempt_number)
        except Exception as exc:
            logger.warning("Failed to roll back session before retry: %s", exc)


def db_retry(func: T) -> T:
    """
    Decorator for retrying database operations on transient errors.

    Uses exponential backoff: wait 2^1, 2^2, 2^3 seconds between attempts.
    Stops after settings.RETRY_MAX_ATTEMPTS.

    Automatically rolls back the SQLAlchemy session before each retry
    to prevent "nested transaction" errors from a previous failed flush.
    """
    return retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT,
        ),
        after=after_log(logger, logging.WARNING),
        before_sleep=_rollback_session_before_retry,
        reraise=True,
        retry=lambda exc: isinstance(exc, DBAPIError),
    )(func)
