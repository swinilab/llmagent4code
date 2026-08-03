"""Observation infrastructure: health, metrics, and the test reset hook.

These paths must remain servable under every condition the contract exercises.
None of them passes through admission control, and none requires a database
round-trip to produce a response - `/health/ready` is the sole exception in
*content*, since it reports the unready state during an outage, but it still
answers promptly rather than hanging.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.metrics import metrics
from app.core.test_hooks import hook_state
from app.persistence.database import check_database_ready
from app.schemas.dto import HealthResponse, MetricsResponse

router = APIRouter()


@router.get(
    "/health/live",
    response_model=HealthResponse,
    operation_id="healthLive",
    summary="Liveness probe",
    description=(
        "Reports whether the process is alive. Answers 200 without touching the "
        "database, so it stays available during a dependency outage."
    ),
    tags=["Observability"],
)
async def health_live() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    operation_id="healthReady",
    summary="Readiness probe",
    description=(
        "Reports whether the service is ready for normal operations. Returns 503 "
        "with `status=not_ready` while the database is unreachable, and recovers "
        "automatically once it returns."
    ),
    responses={503: {"model": HealthResponse, "description": "Not ready for normal operations"}},
    tags=["Observability"],
)
async def health_ready(response: Response) -> HealthResponse:
    database_ready = await run_in_threadpool(check_database_ready)
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="not_ready", database="unavailable")
    return HealthResponse(status="ready", database="available")


@router.get(
    "/internal/admission",
    operation_id="getAdmissionState",
    summary="Admission-control state",
    description=(
        "Reports the configured in-flight limit, the current number of admitted "
        "requests, and the peak observed since the last reset. The peak is "
        "recorded by the admission controller itself at the moment a slot is "
        "taken, so it is the authoritative measure of concurrent admission - "
        "client-observed request windows include connection setup and are not. "
        "Observation infrastructure: bypasses admission control and reads no "
        "database."
    ),
    tags=["Observability"],
)
async def get_admission_state() -> dict[str, int]:
    from app.api.middleware import admission_controller

    return {
        "max_in_flight_requests": admission_controller.max_in_flight,
        "in_flight": admission_controller.in_flight,
        "peak_in_flight": admission_controller.peak_in_flight,
    }


@router.get(
    "/internal/metrics",
    response_model=MetricsResponse,
    operation_id="getMetrics",
    summary="Runtime counters",
    description=(
        "Returns in-process counters incremented at the exact site where each "
        "mechanism executes. Reads no database, so it stays available during an "
        "outage. Counters are monotonic until reset."
    ),
    tags=["Observability"],
)
async def get_metrics() -> MetricsResponse:
    return MetricsResponse(**metrics.snapshot())


@router.post(
    "/internal/test/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="resetTestState",
    summary="Reset in-process test state",
    description=(
        "Available only when `ENABLE_TEST_HOOKS=true`, otherwise 404. Resets all "
        "counters, clears the application cache, and clears injected-fault state. "
        "Business data in PostgreSQL is never deleted, and no database round-trip "
        "is made, so it stays callable during an outage."
    ),
    responses={404: {"description": "Test hooks are disabled"}},
    tags=["Observability"],
)
async def reset_test_state() -> Response:
    if not settings.enable_test_hooks:
        raise HTTPException(status_code=404, detail="Not Found")

    # Imported here so the cache instance is the same one the read path uses.
    from app.api.middleware import admission_controller
    from app.services.product_service import product_cache

    metrics.reset()
    product_cache.clear()
    hook_state.reset()
    admission_controller.reset_peak()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
