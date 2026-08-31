"""Operational endpoints.

These exist so a reviewer can *observe* each NFR rather than take it on trust -
they are the verification surface referenced in docs/VERIFICATION.md.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.api.deps import get_cache
from app.core.errors import ValidationError
from app.infra.cache import EntityCache
from app.infra.database import PrimarySession, ReplicaSession
from app.infra.degradation import cache_breaker, feature_registry, replica_breaker

router = APIRouter(tags=["ops"])


@router.get("/health", summary="Liveness")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness - per-dependency probe")
async def readiness(cache: Annotated[EntityCache, Depends(get_cache)]) -> dict:
    """Reports each dependency independently so partial failure is visible."""
    checks: dict[str, str] = {}

    for label, factory in (("primary", PrimarySession), ("replica", ReplicaSession)):
        try:
            with factory() as session:
                session.execute(text("SELECT 1"))
            checks[label] = "up"
        except Exception as exc:
            checks[label] = f"down: {type(exc).__name__}"

    try:
        await cache._redis.ping()
        checks["redis"] = "up"
    except Exception as exc:
        checks["redis"] = f"down: {type(exc).__name__}"

    # Critical path needs only the primary; the rest are degradable.
    ready = checks["primary"] == "up"
    return {"ready": ready, "checks": checks}


@router.get("/ops/nfr", summary="Live NFR tactic state (NFR 1.1, 1.2, 2.1, 2.2, 2.3)")
async def nfr_status(request: Request, cache: Annotated[EntityCache, Depends(get_cache)]) -> dict:
    limiter = request.app.state.rate_limiter
    resync = request.app.state.resynchronizer
    return {
        "nfr_1_1_limit_event_response": {
            "capacity": limiter.capacity,
            "refillPerSecond": limiter.refill_rate,
            "throttled": request.app.state.metrics["throttled"],
        },
        "nfr_1_2_multiple_copies": {"cache": cache.stats(), "replicaConfigured": True},
        "nfr_2_1_exception_detection": {
            "breakers": {
                cache_breaker.name: cache_breaker.state.value,
                replica_breaker.name: replica_breaker.state.value,
            },
            "detected": request.app.state.metrics["exceptions_detected"],
        },
        "nfr_2_2_graceful_degradation": feature_registry.status(),
        "nfr_2_3_state_resynchronization": (
            resync.last_report.as_dict() if resync.last_report else {"status": "no sweep yet"}
        ),
    }


@router.post("/ops/resync", summary="Force a state resynchronization sweep (NFR 2.3)")
async def force_resync(request: Request) -> dict:
    report = await request.app.state.resynchronizer.run_once()
    return report.as_dict()


@router.post("/ops/degrade/{feature}", summary="Shed a non-critical feature (NFR 2.2 demo)")
async def degrade(feature: str) -> dict:
    """Critical features are never sheddable - the attempt is a 400, not a fault."""
    try:
        feature_registry.shed(feature)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return feature_registry.status()


@router.post("/ops/restore/{feature}", summary="Restore a shed feature (NFR 2.2 demo)")
async def restore(feature: str) -> dict:
    feature_registry.restore(feature)
    return feature_registry.status()
