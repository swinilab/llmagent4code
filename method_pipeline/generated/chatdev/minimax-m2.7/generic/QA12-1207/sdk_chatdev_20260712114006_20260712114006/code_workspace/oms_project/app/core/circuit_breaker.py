"""
OMS Core Circuit Breaker.
Implements fault detection and recovery pattern for external service calls.
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps

from app.core.events import EventType, publish_event


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing, reject calls
    HALF_OPEN = "HALF_OPEN" # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    Tracks failures and opens circuit when threshold is reached.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitOpenError(f"Circuit {self.name} is OPEN")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(f"Circuit {self.name} is HALF_OPEN, max calls reached")
                self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to_half_open(self):
        """Transition circuit to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        publish_event(
            EventType.CIRCUIT_OPEN,
            {"circuit": self.name, "state": CircuitState.HALF_OPEN.value}
        )

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self._transition_to_closed()
            else:
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self):
        """Transition circuit to open state."""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        publish_event(
            EventType.CIRCUIT_OPEN,
            {"circuit": self.name, "state": CircuitState.OPEN.value}
        )

    def _transition_to_closed(self):
        """Transition circuit to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        publish_event(
            EventType.CIRCUIT_CLOSED,
            {"circuit": self.name}
        )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self.state

    def reset(self):
        """Manually reset circuit to closed state."""
        with self._lock:
            self._transition_to_closed()


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _breakers: Dict[str, CircuitBreaker] = {}
    _lock = threading.RLock()

    @classmethod
    def get(cls, name: str, **config) -> CircuitBreaker:
        """Get or create circuit breaker by name."""
        with cls._lock:
            if name not in cls._breakers:
                cls._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=config.get('failure_threshold', 5),
                    recovery_timeout=config.get('recovery_timeout', 30.0),
                    half_open_max_calls=config.get('half_open_max_calls', 3)
                )
            return cls._breakers[name]

    @classmethod
    def all(cls) -> Dict[str, CircuitBreaker]:
        """Get all registered circuit breakers."""
        with cls._lock:
            return dict(cls._breakers)

    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers."""
        with cls._lock:
            for breaker in cls._breakers.values():
                breaker.reset()


def circuit_breaker(name: str, **config):
    """Decorator to add circuit breaker protection to a function."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        breaker = CircuitBreakerRegistry.get(name, **config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
