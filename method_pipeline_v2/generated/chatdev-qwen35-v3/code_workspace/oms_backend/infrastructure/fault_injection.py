"""
Fault injection module for testing NFR 2.1 (Exception Detection) and NFR 2.2 (Graceful Degradation)
Provides controllable fault injection for verification suite
"""
import asyncio
import time
from typing import Optional, Callable, Any
from functools import wraps
from oms_backend.config.settings import get_settings

settings = get_settings()


class FaultInjector:
    """
    Fault injection system for testing availability tactics.
    Implements NFR 2.1 (Exception Detection) and NFR 2.2 (Graceful Degradation).
    
    Tactics:
    - Availability > Detect Faults > Timeout
    - Availability > Recover from Faults > Graceful Degradation
    """
    
    def __init__(self):
        self.enabled = settings.fault_injection_enabled
        self.fault_type = settings.fault_type  # "timeout", "error", "slow"
        self.fault_duration_ms = settings.fault_duration_ms
        self._fault_start_time: Optional[float] = None
        self._fault_active = False
    
    def enable_fault(self, fault_type: str, duration_ms: int = 5000) -> None:
        """Enable fault injection"""
        self.enabled = True
        self.fault_type = fault_type
        self.fault_duration_ms = duration_ms
        self._fault_start_time = time.time()
        self._fault_active = True
    
    def disable_fault(self) -> None:
        """Disable fault injection"""
        self.enabled = False
        self._fault_active = False
        self._fault_start_time = None
    
    def is_fault_active(self) -> bool:
        """Check if fault is currently active"""
        if not self.enabled or not self._fault_active:
            return False
        
        # Check if fault duration has elapsed
        if self._fault_start_time:
            elapsed_ms = (time.time() - self._fault_start_time) * 1000
            if elapsed_ms >= self.fault_duration_ms:
                self.disable_fault()
                return False
        return True
    
    def inject(self) -> None:
        """Inject fault based on configured type"""
        if not self.is_fault_active():
            return
        
        if self.fault_type == "timeout":
            # Simulate timeout by sleeping longer than timeout threshold
            time.sleep(settings.default_timeout_seconds + 1)
        elif self.fault_type == "error":
            # Simulate error by raising exception
            raise ConnectionError("Injected fault: connection failed")
        elif self.fault_type == "slow":
            # Simulate slow response
            time.sleep(self.fault_duration_ms / 1000)
    
    async def inject_async(self) -> None:
        """Inject fault asynchronously"""
        if not self.is_fault_active():
            return
        
        if self.fault_type == "timeout":
            await asyncio.sleep(settings.default_timeout_seconds + 1)
        elif self.fault_type == "error":
            raise ConnectionError("Injected fault: connection failed")
        elif self.fault_type == "slow":
            await asyncio.sleep(self.fault_duration_ms / 1000)
    
    def wrap(self, func: Callable) -> Callable:
        """Decorator to wrap a function with fault injection"""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if self.is_fault_active():
                await self.inject_async()
            return await func(*args, **kwargs)
        return wrapper


# Global fault injector instance
fault_injector = FaultInjector()
