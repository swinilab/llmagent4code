"""
Health check endpoints for fault detection
"""
from datetime import datetime
from app.db.connection_pool import health_check as db_health_check
from app.queue.queue_manager import get_queue_manager
from app.degradation.degradation_manager import get_degradation_manager


async def liveness_check() -> dict:
    """
    Liveness probe - checks if application is running.
    Implements Ping/Echo tactic for fault detection.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


async def readiness_check() -> dict:
    """
    Readiness probe - checks if application is ready to serve requests.
    Verifies database connectivity and critical dependencies.
    """
    db_healthy = await db_health_check()
    queue_manager = get_queue_manager()
    degradation = get_degradation_manager()
    
    return {
        "status": "ready" if db_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            "queue_size": queue_manager.size(),
            "degradation_level": degradation.level.value,
        },
    }


async def health_check() -> dict:
    """
    Comprehensive health check including all components.
    """
    db_healthy = await db_health_check()
    queue_manager = get_queue_manager()
    degradation = get_degradation_manager()
    queue_stats = queue_manager.get_stats()
    degradation_status = degradation.get_status()
    
    overall_healthy = db_healthy and degradation.level.value != "CRITICAL"
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
            },
            "queue": queue_stats,
            "degradation": degradation_status,
        },
    }
