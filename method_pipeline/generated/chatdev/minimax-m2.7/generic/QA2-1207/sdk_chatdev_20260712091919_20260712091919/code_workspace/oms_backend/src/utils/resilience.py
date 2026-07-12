"""
Resilience utilities for NFR 2.1 (Graceful Degradation), NFR 2.2 (Fault Detection), NFR 2.3 (State Preservation).
"""
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "snapshots")


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3


class CircuitBreaker:
    """
    Circuit breaker implementation for graceful degradation (NFR 2.1).
    Prevents cascade failures by opening circuit when failure threshold is reached.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def _should_attempt_recovery(self) -> bool:
        if self._last_failure_time is None:
            return False
        return (time.time() - self._last_failure_time) >= self.config.recovery_timeout

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return False

    def record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= 2:
                    self._reset()
            else:
                self._failure_count = 0
            logger.debug(f"Circuit {self.name}: success recorded, state={self._state}")

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: half-open failure, opening circuit")
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: failure threshold reached, opening circuit")
            logger.debug(f"Circuit {self.name}: failure recorded, count={self._failure_count}")

    def _reset(self):
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            logger.info(f"Circuit {self.name}: reset to closed state")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time
            }


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to apply circuit breaker pattern to a function."""
    cb = CircuitBreaker(name, config)
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cb.allow_request():
                raise CircuitBreakerOpen(f"Circuit {name} is open")
            try:
                result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise
        return wrapper
    setattr(wrapper, '_circuit_breaker', cb)
    return decorator


def with_retry(max_attempts: int = 3, backoff_factor: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator to retry a function on exception with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Base delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
    
    Example:
        @with_retry(max_attempts=3, backoff_factor=0.5)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {delay:.2f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator


class RetryStrategy:
    """
    Retry strategy with exponential backoff for fault recovery (NFR 2.2).
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = delay * 0.1 * (hash(str(time.time())) % 100) / 100
        return delay + jitter

    def execute(self, func: Callable, *args, **kwargs):
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} for {func.__name__} after {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for {func.__name__}: {e}")
        raise last_exception


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class FeatureFlags:
    """
    Feature flags for graceful degradation (NFR 2.1).
    Allows disabling non-essential features under resource contention.
    """
    
    def __init__(self):
        self._flags: Dict[str, bool] = {
            "audit_log_enabled": True,
            "payment_gateway_enabled": True,
            "non_core_features_enabled": True,
            "analytics_enabled": True,
            "notifications_enabled": True
        }
        self._lock = threading.RLock()
    
    def is_enabled(self, flag_name: str) -> bool:
        with self._lock:
            return self._flags.get(flag_name, False)
    
    def set_flag(self, flag_name: str, enabled: bool):
        with self._lock:
            self._flags[flag_name] = enabled
            logger.info(f"Feature flag '{flag_name}' set to {enabled}")
    
    def get_all_flags(self) -> Dict[str, bool]:
        with self._lock:
            return dict(self._flags)
    
    def disable_non_core_features(self):
        """Disable non-essential features for graceful degradation."""
        with self._lock:
            self._flags["non_core_features_enabled"] = False
            self._flags["analytics_enabled"] = False
            self._flags["notifications_enabled"] = False
            logger.warning("Non-core features disabled for graceful degradation")

    def disable_non_essential(self):
        """Disable non-essential features for graceful degradation."""
        with self._lock:
            self._flags["non_core_features_enabled"] = False
            self._flags["analytics_enabled"] = False
            self._flags["notifications_enabled"] = False
            self._flags["audit_log_enabled"] = False
            logger.warning("Non-essential features disabled for graceful degradation")

    def enable_all(self):
        """Re-enable all features."""
        with self._lock:
            self._flags["non_core_features_enabled"] = True
            self._flags["analytics_enabled"] = True
            self._flags["notifications_enabled"] = True
            self._flags["audit_log_enabled"] = True
            self._flags["payment_gateway_enabled"] = True
            logger.info("All features re-enabled")


class StateManager:
    """
    State manager for crash recovery (NFR 2.3).
    Maintains state snapshots that allow recovery after unexpected shutdown.
    """
    
    def __init__(self, snapshot_dir: str = SNAPSHOT_DIR):
        self._snapshot_path = snapshot_dir
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        os.makedirs(snapshot_dir, exist_ok=True)
        self._load_existing_snapshots()
    
    def _snapshot_path_for(self, entity_type: str, entity_id: str) -> str:
        return os.path.join(self._snapshot_path, f"{entity_type}_{entity_id}.json")
    
    def _load_existing_snapshots(self):
        """Load existing snapshots from disk on startup."""
        try:
            if os.path.exists(self._snapshot_path):
                for filename in os.listdir(self._snapshot_path):
                    if filename.endswith(".json"):
                        filepath = os.path.join(self._snapshot_path, filename)
                        with open(filepath, "r") as f:
                            data = json.load(f)
                            key = f"{data.get('entity_type', 'unknown')}_{data.get('entity_id', '')}"
                            self._snapshots[key] = data
            logger.info(f"Loaded {len(self._snapshots)} existing state snapshots")
        except Exception as e:
            logger.warning(f"Could not load existing snapshots: {e}")

    def save_snapshot(self, entity_type: str, entity_id: str, state: Dict[str, Any], 
                      last_event: str = "") -> str:
        """Save a state snapshot for potential crash recovery."""
        snapshot = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": state,
            "last_event": last_event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_id": str(uuid4())
        }
        
        with self._lock:
            key = f"{entity_type}_{entity_id}"
            self._snapshots[key] = snapshot
            
            filepath = self._snapshot_path_for(entity_type, entity_id)
            with open(filepath, "w") as f:
                json.dump(snapshot, f, indent=2)
        
        logger.debug(f"Saved snapshot for {entity_type}/{entity_id}")
        return snapshot["snapshot_id"]

    def get_snapshot(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for an entity."""
        with self._lock:
            key = f"{entity_type}_{entity_id}"
            return self._snapshots.get(key)

    def get_all_pending_recoveries(self) -> List[Dict[str, Any]]:
        """Get all entities that have snapshots but may not have completed processing."""
        with self._lock:
            return [
                {"entity_type": s["entity_type"], "entity_id": s["entity_id"], 
                 "timestamp": s["timestamp"], "last_event": s.get("last_event", "")}
                for s in self._snapshots.values()
            ]

    def clear_snapshot(self, entity_type: str, entity_id: str):
        """Clear snapshot after successful processing."""
        with self._lock:
            key = f"{entity_type}_{entity_id}"
            if key in self._snapshots:
                del self._snapshots[key]
            
            filepath = self._snapshot_path_for(entity_type, entity_id)
            if os.path.exists(filepath):
                os.remove(filepath)

    def generate_idempotency_key(self, prefix: str = "") -> str:
        """Generate a unique idempotency key."""
        if prefix:
            return f"{prefix}_{uuid4()}"
        return str(uuid4())


class HealthChecker:
    """
    Health checker for fault detection (NFR 2.2).
    Monitors component health and provides recovery status.
    """
    
    def __init__(self):
        self._components: Dict[str, Dict[str, Any]] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
    
    def register_component(self, name: str, health_fn: Callable[[], bool], 
                          circuit_breaker: Optional[CircuitBreaker] = None):
        """Register a component for health monitoring."""
        with self._lock:
            self._components[name] = {
                "name": name,
                "health_fn": health_fn,
                "status": "unknown",
                "last_check": None,
                "failure_count": 0
            }
            if circuit_breaker:
                self._circuit_breakers[name] = circuit_breaker
    
    def register_circuit_breaker(self, name: str, cb: CircuitBreaker):
        """Register a circuit breaker for monitoring."""
        with self._lock:
            self._circuit_breakers[name] = cb
    
    def check_health(self, name: str) -> Dict[str, Any]:
        """Check health of a specific component."""
        with self._lock:
            if name not in self._components:
                return {"status": "not_registered", "name": name}
            
            component = self._components[name]
            try:
                is_healthy = component["health_fn"]()
                component["status"] = "healthy" if is_healthy else "unhealthy"
                component["last_check"] = datetime.now(timezone.utc).isoformat()
                component["failure_count"] = 0
            except Exception as e:
                component["status"] = "unhealthy"
                component["last_check"] = datetime.now(timezone.utc).isoformat()
                component["failure_count"] = component.get("failure_count", 0) + 1
                logger.error(f"Health check failed for {name}: {e}")

            result = {
                "name": name,
                "status": component["status"],
                "last_check": component["last_check"],
                "failure_count": component.get("failure_count", 0)
            }
            
            if name in self._circuit_breakers:
                result["circuit_breaker"] = self._circuit_breakers[name].get_stats()
            
            return result

    def check_all_health(self) -> Dict[str, Any]:
        """Check health of all registered components."""
        results = {}
        overall_healthy = True
        
        with self._lock:
            component_names = list(self._components.keys())
        
        for name in component_names:
            result = self.check_health(name)
            results[name] = result
            if result["status"] != "healthy":
                overall_healthy = False
        
        return {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "components": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
