"""
Retry with exponential backoff for transient failures (NFR 2.2).

Uses tenacity library for configurable retry policies.
"""
from __future__ import annotations

from typing import Any, Callable

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.stop import stop_never

from oms.config import settings

import logging

logger = logging.getLogger(__name__)


def db_retry_policy():
    """Retry policy for transient DB errors (connection drops, deadlocks)."""
    return AsyncRetrying(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            multiplier=settings.retry_base_delay_ms / 1000,
            min=0.1,
            max=5.0,
        ),
        retry=retry_if_exception_type(
            (ConnectionError, TimeoutError, OSError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


async def with_db_retry(func: Callable, *args, **kwargs) -> Any:
    """Execute func with exponential backoff retry for DB transient errors."""
    async for attempt in db_retry_policy():
        with attempt:
            return await func(*args, **kwargs)
