"""
Health check endpoint (NFR 2.2).

Used by monitoring systems and orchestration tools to detect
component failures and trigger recovery.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.domain.schemas import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns the status of the application and its dependencies.
    Used by systemd, Docker, and monitoring tools for fault detection.
    """
    service = HealthService()
    return await service.get_health()
