"""
Health check endpoints and system diagnostics.
Provides liveness, readiness, degradation, queue, and state endpoints.
"""
from __future__ import annotations

import time

from fastapi import APIRouter

from app.database import async_session_factory
from app.infrastructure.graceful_degradation import GracefulDegradationManager
from app.infrastructure.queue_manager import QueueManager
from app.infrastructure.state_manager import StateManager


def create_health_router(
    queue_mgr: QueueManager,
    degradation_mgr: GracefulDegradationManager,
    state_mgr: StateManager,
    startup_time: float,
) -> APIRouter:
    """Factory to inject dependencies into health endpoints.
    Creates a fresh APIRouter instance on every call to avoid
    shared-mutable-state issues when the factory is invoked more
    than once (e.g. in tests or after module reload).
    """
    router = APIRouter(tags=["Health"])

    @router.get("/health/live")
    async def liveness():
        """Simple liveness probe — always returns 200 if the process is alive."""
        return {"status": "alive", "uptime_seconds": round(time.monotonic() - startup_time, 2)}

    @router.get("/health/ready")
    async def readiness():
        """Readiness probe — checks database connectivity."""
        try:
            async with async_session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "detail": str(exc)},
            )

    @router.get("/health/degradation")
    async def degradation_status():
        """Return current degradation state."""
        ds = degradation_mgr.state
        return {
            "degraded": ds.degraded,
            "product_search_disabled": ds.product_search_disabled,
            "order_history_disabled": ds.order_history_disabled,
            "invoice_listing_disabled": ds.invoice_listing_disabled,
            "reason": ds.reason,
        }

    @router.get("/health/queue")
    async def queue_status():
        """Return queue metrics."""
        return {
            "queue_size": queue_mgr.queue_size,
            "peak_queue_size": queue_mgr.peak_queue_size,
            "dropped_count": queue_mgr.dropped_count,
            "processed_count": queue_mgr.processed_count,
            "error_count": queue_mgr.error_count,
        }

    @router.get("/health/state")
    async def state_status():
        """Return state manager info."""
        return {
            "last_heartbeat": state_mgr.last_heartbeat.isoformat() if state_mgr.last_heartbeat else None,
        }

    return router
