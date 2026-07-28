"""
Combine health endpoints into a single router.
"""

from fastapi import APIRouter
from app.health.liveness import router as liveness_router

router = APIRouter()
router.include_router(liveness_router)
