"""
Health and metrics endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from oms.infrastructure.metrics import get_metrics

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)
