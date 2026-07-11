"""
Health-check service (NFR 2.2 – Fault Detection and Recovery).

Provides:
- /health/ping – lightweight liveness probe
- /health/readiness – checks DB connectivity
- /health/degradation – reports current degradation status
"""
import logging
import time
from typing import Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from oms.config import settings
from oms.services.circuit_breaker import CircuitBreaker
from oms.utils.system import get_cpu_percent, get_mem_percent

logger = logging.getLogger(__name__)


class HealthService:
    """
    Exposes health probes. The DB check uses a circuit breaker so that
    repeated failures do not cascade.
    """

    def __init__(self):
        self._db_circuit = CircuitBreaker(
            "db_health",
            failure_threshold=3,
            recovery_timeout=15.0,
            half_open_max_calls=2,
        )
        self._start_time = time.monotonic()

    def ping(self) -> Dict:
        """Lightweight liveness check."""
        return {
            "status": "alive",
            "uptime_seconds": round(time.monotonic() - self._start_time, 2),
        }

    def readiness(self, db: Session) -> Dict:
        """Check DB connectivity via a simple SELECT 1."""

        def _check_db() -> str:
            db.execute(text("SELECT 1"))
            return "healthy"

        def _fallback() -> str:
            return "unhealthy"

        db_status = self._db_circuit.call(_check_db, _fallback)
        return {
            "status": "ready" if db_status == "healthy" else "degraded",
            "database": db_status,
        }

    def degradation_status(self) -> Dict:
        """Report CPU/memory load and whether degradation is active."""
        cpu_pct = get_cpu_percent()
        mem_pct = get_mem_percent()
        degraded = (
            cpu_pct > settings.DEGRADATION_CPU_THRESHOLD
            or mem_pct > settings.DEGRADATION_MEM_THRESHOLD
        )
        return {
            "degraded": degraded,
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "cpu_threshold": settings.DEGRADATION_CPU_THRESHOLD,
            "memory_threshold": settings.DEGRADATION_MEM_THRESHOLD,
        }
