from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.health_service import HealthService

router = APIRouter(tags=["system"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    report = await HealthService(
        request.app.state.session_factory,
        request.app.state.redis,
        timeout_seconds=request.app.state.settings.dependency_timeout_seconds,
    ).check()
    return JSONResponse(status_code=200 if report["criticalReady"] else 503, content=report)


@router.post("/internal/resynchronize")
async def resynchronize(request: Request) -> dict[str, int]:
    report = await request.app.state.state_synchronizer.resynchronize_once()
    return asdict(report)

