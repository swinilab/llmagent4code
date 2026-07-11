"""
Retry policy with exponential backoff (NFR 2.2 Fault Detection and Recovery).

Uses the `tenacity` library for robust retry logic. Configured with:
  - Exponential backoff: base 2, max 30 seconds.
  - Jitter to avoid thundering herd.
  - Configurable max retries.
  - Only retries on transient errors (connection errors, timeouts).

Trade-off (NFR 1.1 vs NFR 2.2):
  Retries add latency. For the latency-critical checkout path, we limit
  retries to 2 attempts with a short backoff. For non-critical background
  operations, we allow more retries.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Type, Union

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

# Transient errors that should be retried
TRANSIENT_EXCEPTIONS: tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def default_retry_policy(
    attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 30.0,
    jitter: float = 0.1,
) -> AsyncRetrying:
    """Create a standard retry policy with exponential backoff + jitter.

    Args:
        attempts: Maximum number of retry attempts.
        min_wait: Initial wait time in seconds.
        max_wait: Maximum wait time in seconds.
        jitter: Random jitter factor.

    Returns:
        An AsyncRetrying instance.
    """
    return AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(
            initial=min_wait,
            max=max_wait,
            jitter=jitter,
        ),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Fast-path retry policy for checkout (NFR 1.1 sensitivity)
checkout_retry_policy = default_retry_policy(
    attempts=2,
    min_wait=0.1,
    max_wait=1.0,
    jitter=0.05,
)

# Background task retry policy (more tolerant of latency)
background_retry_policy = default_retry_policy(
    attempts=5,
    min_wait=1.0,
    max_wait=60.0,
    jitter=0.5,
)
