"""
Health check router (NFR 2.2 – Fault Detection and Recovery).
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.services.health_service import HealthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["Health"])
health_service = HealthService()


@router.get("/ping")
def ping():
    """Liveness probe – always returns 200 if the process is alive."""
    return health_service.ping()


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe – checks DB connectivity."""
    return health_service.readiness(db)


@router.get("/degradation")
def degradation():
    """Returns current degradation status."""
    return health_service.degradation_status()
