"""
Health check endpoints and component monitoring (NFR 2.2).

Provides:
  - /health: overall system health (DB, Redis, RabbitMQ)
  - /health/ready: readiness probe
  - /health/live: liveness probe
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from oms.infrastructure.cache import cache
from oms.infrastructure.database import async_session_factory
from oms.infrastructure.message_queue import mq

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


async def _check_db() -> bool:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
        return False


async def _check_redis() -> bool:
    """Check Redis connectivity using the public ping() method."""
    return await cache.ping()


async def _check_rabbitmq() -> bool:
    try:
        if mq._connection and not mq._connection.is_closed:
            return True
        return False
    except Exception:
        return False


@router.get("/health")
async def health():
    """Full health check — all dependencies."""
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    mq_ok = await _check_rabbitmq()
    all_ok = db_ok and redis_ok and mq_ok
    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
            "rabbitmq": "up" if mq_ok else "down",
        },
    }


@router.get("/health/ready")
async def readiness():
    """Readiness probe — is the service ready to accept traffic?"""
    db_ok = await _check_db()
    return {"status": "ready" if db_ok else "not_ready"}


@router.get("/health/live")
async def liveness():
    """Liveness probe — is the process alive?"""
    return {"status": "alive"}
