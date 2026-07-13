import time
import functools
import logging
import random
from enum import Enum
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func: Callable, *args, **kwargs):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

def retry(
    exceptions: Type[Exception] | tuple[Type[Exception], ...] = Exception,
    tries: int = 3,
    delay: float = 1,
    backoff: float = 2,
    jitter: float = 0.1,
):
    """
    Retry decorator with exponential backoff and optional jitter.

    :param exceptions: exception type(s) to catch and retry on
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay in seconds
    :param backoff: multiplier applied to delay after each try
    :param jitter: extra seconds added to delay randomly (helps prevent thundering herd)
    """
    def deco_retry(f: Callable):
        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{str(e)}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
                    mdelay += jitter * (2 * random.random() - 1)  # random jitter
            return f(*args, **kwargs)
        return f_retry
    return deco_retry