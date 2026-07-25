"""
Health check controller
"""
from fastapi import APIRouter
from app.health.liveness import liveness_check, readiness_check, health_check
from app.queue.queue_manager import get_queue_manager
from app.degradation.degradation_manager import get_degradation_manager

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/live")
async def liveness():
    """Liveness probe endpoint"""
    return await liveness_check()


@router.get("/ready")
async def readiness():
    """Readiness probe endpoint"""
    return await readiness_check()


@router.get("")
async def health():
    """Comprehensive health check endpoint"""
    return await health_check()


@router.get("/queue")
async def queue_status():
    """Get queue status for load monitoring"""
    queue_manager = get_queue_manager()
    return queue_manager.get_stats()


@router.get("/degradation")
async def degradation_status():
    """Get degradation status"""
    degradation = get_degradation_manager()
    return degradation.get_status()
