"""
Health service: provides system health information (NFR 2.2).

The health endpoint is used by monitoring systems and orchestration
tools to detect component failures and trigger recovery.
"""
from __future__ import annotations

import logging

from app.infrastructure.lifecycle import check_database_health, get_uptime

logger = logging.getLogger(__name__)


class HealthService:
    """Provides health check information."""

    async def get_health(self) -> dict:
        """Return current system health status."""
        db_healthy = await check_database_health()
        uptime = get_uptime()

        status = "healthy" if db_healthy else "degraded"

        return {
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "uptime_seconds": round(uptime, 2),
        }
