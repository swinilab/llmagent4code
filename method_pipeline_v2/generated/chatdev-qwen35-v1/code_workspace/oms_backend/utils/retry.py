"""
Retry utilities for NFR 2.3 - State Resynchronization and NFR 2.2 - Graceful Degradation
Uses tenacity for retry logic with exponential backoff
"""
from typing import Callable, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
from oms_backend.config import settings
from oms_backend.utils.exceptions import TimeoutException, ServiceUnavailableException


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 10.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Create a retry decorator with exponential backoff.
    Satisfies NFR 2.3: State Resynchronization through retry on transient failures.
    Satisfies NFR 2.2: Graceful Degradation by allowing retries before failing.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        retryable_exceptions: Tuple of exception types that should trigger retry
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retryable_exceptions),
            reraise=True,
        )(func)
    return decorator


def execute_with_retry(
    operation: Callable[[], Any],
    operation_name: str,
    max_attempts: int = 3,
    timeout_seconds: Optional[int] = None
) -> Any:
    """
    Execute an operation with retry logic.
    
    Args:
        operation: Callable to execute
        operation_name: Name of the operation for error messages
        max_attempts: Maximum number of retry attempts
        timeout_seconds: Timeout for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        RetryError: If all retry attempts fail
        TimeoutException: If operation times out
    """
    timeout = timeout_seconds or settings.transaction_timeout_seconds
    
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=0.5, max=10.0),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _execute():
        return operation()
    
    try:
        return _execute()
    except RetryError as e:
        raise ServiceUnavailableException(
            service_name=operation_name,
            fallback_available=False
        ) from e
    except TimeoutError as e:
        raise TimeoutException(operation=operation_name, timeout_seconds=timeout) from e


def synchronize_state(
    primary_state: Any,
    standby_state: Any,
    comparison_fn: Callable[[Any, Any], bool],
    sync_fn: Callable[[Any], Any],
    max_attempts: int = 3
) -> bool:
    """
    Synchronize state between active and standby components.
    Satisfies NFR 2.3: State Resynchronization - states are periodically compared.
    
    Args:
        primary_state: State of the primary/active component
        standby_state: State of the standby component
        comparison_fn: Function to compare states (returns True if synchronized)
        sync_fn: Function to synchronize standby state from primary
        max_attempts: Maximum retry attempts for synchronization
        
    Returns:
        True if synchronization successful, False otherwise
    """
    if comparison_fn(primary_state, standby_state):
        return True  # Already synchronized
    
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=0.5, max=5.0),
        reraise=False,
    )
    def _sync():
        new_standby_state = sync_fn(primary_state)
        if not comparison_fn(primary_state, new_standby_state):
            raise Exception("Synchronization failed")
        return new_standby_state
    
    try:
        _sync()
        return True
    except RetryError:
        return False
