
\"\"\"\
Resilience utilities for the Order Management System.\
Includes retry logic and circuit breaker-like mechanisms to satisfy NFR 2.1 and 2.2.\
\"\"\"
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Type
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import SQLAlchemyError, OperationalError

logger = logging.getLogger(__name__)

# Define transient exceptions that should trigger a retry
TRANSIENT_EXCEPTIONS = (
    OperationalError, 
    SQLAlchemyError, 
    asyncio.TimeoutError
)

def resilience_retry():
    \"\"\"
    Decorator to provide exponential backoff retry for transient failures.
    Satisfies NFR 2.2 (Fault Detection and Recovery).
    \"\"\"
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        reraise=True
    )

def circuit_breaker_timeout(timeout_seconds: float = 5.0):
    \"\"\"
    Decorator to wrap a function with a timeout.
    If the timeout is reached, it raises a TimeoutError which can be caught by 
    the resilience_retry or global middleware.
    Satisfies NFR 2.1 (Graceful Degradation) by preventing hanging requests.
    \"\"\"
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError as e:
                logger.error(f"Circuit breaker timeout reached for {func.__name__}")
                raise e
        return wrapper
    return decorator
