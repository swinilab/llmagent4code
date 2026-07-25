"""
Graceful degradation manager for handling resource contention
"""
import asyncio
from enum import Enum
from typing import Dict, Set
from datetime import datetime
from app.config.settings import Settings

settings = Settings()


class DegradationLevel(Enum):
    """System degradation levels"""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class DegradationManager:
    """
    Manages graceful degradation under resource contention.
    Ensures core checkout functionality remains available during high load.
    """
    
    # Core endpoints that must remain available
    CORE_ENDPOINTS = {
        "/api/v1/orders",
        "/api/v1/orders/{id}",
        "/api/v1/payments",
        "/api/v1/checkout",
    }
    
    # Non-essential endpoints that can be disabled
    NON_ESSENTIAL_ENDPOINTS = {
        "/api/v1/products",
        "/api/v1/customers",
        "/api/v1/invoices",
        "/api/v1/health/queue",
    }
    
    def __init__(self):
        self.level = DegradationLevel.NORMAL
        self.disabled_endpoints: Set[str] = set()
        self.last_check: datetime = datetime.utcnow()
        self._lock = asyncio.Lock()
        self.load_threshold_high = 0.8
        self.load_threshold_critical = 0.95
        self.current_load = 0.0
    
    async def update_load(self, queue_size: int, max_queue: int):
        """Update system load based on queue utilization"""
        async with self._lock:
            self.current_load = queue_size / max_queue if max_queue > 0 else 0
            self.last_check = datetime.utcnow()
            await self._evaluate_degradation()
    
    async def _evaluate_degradation(self):
        """Evaluate and adjust degradation level"""
        if self.current_load >= self.load_threshold_critical:
            self.level = DegradationLevel.CRITICAL
            self.disabled_endpoints = self.NON_ESSENTIAL_ENDPOINTS.copy()
        elif self.current_load >= self.load_threshold_high:
            self.level = DegradationLevel.DEGRADED
            self.disabled_endpoints = set()  # Maybe disable some non-critical
        else:
            self.level = DegradationLevel.NORMAL
            self.disabled_endpoints = set()
    
    def is_endpoint_available(self, path: str) -> bool:
        """Check if endpoint is available (not disabled due to degradation)"""
        # Normalize path
        normalized = path.split("?")[0]
        
        # Core endpoints always available
        for core in self.CORE_ENDPOINTS:
            if normalized.startswith(core.rstrip("/{id}")):
                return True
        
        # Check if disabled
        if normalized in self.disabled_endpoints:
            return False
        
        return True
    
    def get_status(self) -> dict:
        """Get degradation status"""
        return {
            "level": self.level.value,
            "current_load": self.current_load,
            "disabled_endpoints": list(self.disabled_endpoints),
            "core_endpoints_available": len(self.CORE_ENDPOINTS),
            "last_check": self.last_check.isoformat(),
        }
    
    async def recover(self):
        """Attempt to recover from degraded state"""
        async with self._lock:
            self.current_load = 0
            await self._evaluate_degradation()


# Global instance
_degradation_manager: DegradationManager = None


def get_degradation_manager() -> DegradationManager:
    """Get or create global degradation manager"""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = DegradationManager()
    return _degradation_manager
