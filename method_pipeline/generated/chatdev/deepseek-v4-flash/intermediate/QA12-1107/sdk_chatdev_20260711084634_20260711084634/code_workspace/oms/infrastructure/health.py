"""
Health check endpoints and component monitoring (NFR 2.2).

Provides:
  - /health/live: Liveness probe (is the process alive?)
  - /health/ready: Readiness probe (are dependencies reachable?)
  - /health/circuits: Circuit breaker states
  - /health/queue: Queue backlog depth
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from oms.infrastructure.cache import check_cache_health
from oms.infrastructure.circuit_breaker import get_all_circuit_states
from oms.infrastructure.database import check_db_health
from oms.infrastructure.queue import get_stream_length

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.monotonic()


@router.get("/live")
async def liveness() -> dict[str, Any]:
    """Simple liveness probe — always returns 200 if the process is running."""
    uptime_seconds = time.monotonic() - _start_time
    return {
        "status": "alive",
        "uptime_seconds": round(uptime_seconds, 2),
    }


@router.get("/ready")
async def readiness() -> JSONResponse:
    """Readiness probe — checks all dependencies."""
    db_ok = await check_db_health()
    cache_ok = await check_cache_health()

    all_ok = db_ok and cache_ok
    status_code = 200 if all_ok else 503
    content = {
        "status": "ready" if all_ok else "degraded",
        "checks": {
            "database": "pass" if db_ok else "fail",
            "cache": "pass" if cache_ok else "fail",
        },
    }
    return JSONResponse(content=content, status_code=status_code)


@router.get("/circuits")
async def circuit_states() -> dict[str, Any]:
    """Return the state of all circuit breakers."""
    return {
        "circuits": get_all_circuit_states(),
    }


@router.get("/queue")
async def queue_depth() -> dict[str, Any]:
    """Return the backlog depth of task queues."""
    depths: dict[str, int] = {}
    for stream in ("orders:invoice", "orders:ship", "orders:notify"):
        try:
            depth = await get_stream_length(stream)
            depths[stream] = depth
        except Exception as exc:
            depths[stream] = -1
            logger.warning("Failed to check queue depth for %s: %s", stream, exc)
    return {"queue_depths": depths}
