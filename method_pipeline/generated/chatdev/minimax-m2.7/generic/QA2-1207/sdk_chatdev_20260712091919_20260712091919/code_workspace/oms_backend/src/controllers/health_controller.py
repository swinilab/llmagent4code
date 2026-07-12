"""
Health Controller - Health check endpoints for NFR 2.2 Fault Detection and Recovery.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
import json
import os

from ..infrastructure.database import check_db_health, SessionLocal
from ..utils.resilience import HealthChecker, FeatureFlags, StateManager, CircuitBreaker, CircuitBreakerConfig

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, Any]
    feature_flags: Dict[str, bool]


class NFRVerificationResponse(BaseModel):
    nfr_2_1_graceful_degradation: Dict[str, Any]
    nfr_2_2_fault_detection: Dict[str, Any]
    nfr_2_3_state_preservation: Dict[str, Any]


_health_checker = None
_feature_flags = None
_state_manager = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        _health_checker.register_component("database", lambda: check_db_health())
    return _health_checker


def get_feature_flags() -> FeatureFlags:
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
        _feature_flags.set_flag("audit_log_enabled", True)
        _feature_flags.set_flag("payment_gateway_enabled", True)
        _feature_flags.set_flag("non_core_features_enabled", True)
    return _feature_flags


def get_state_manager() -> StateManager:
    global _state_manager
    if _state_manager is None:
        snapshot_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "snapshots")
        _state_manager = StateManager(snapshot_path)
    return _state_manager


@router.get("", response_model=HealthResponse)
def health_check():
    """
    Overall system health check combining component health and feature flags.
    """
    checker = get_health_checker()
    flags = get_feature_flags()
    
    health = checker.check_all_health()
    
    return HealthResponse(
        status=health["overall_status"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=health["components"],
        feature_flags=flags.get_all_flags()
    )


@router.get("/live")
def liveness_check():
    """
    Kubernetes liveness probe.
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready")
def readiness_check():
    """
    Kubernetes readiness probe.
    Returns 200 if the application is ready to accept traffic.
    """
    checker = get_health_checker()
    health = checker.check_all_health()
    
    if health["overall_status"] == "healthy":
        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
    else:
        return {"status": "not_ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/db")
def database_health():
    """
    Detailed database health check.
    """
    is_healthy = check_db_health()
    return {
        "database": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/nfr-verification", response_model=NFRVerificationResponse)
def nfr_verification():
    """
    Verify all NFR mechanisms are functioning.
    Returns detailed status of NFR 2.1, 2.2, and 2.3 implementations.
    """
    checker = get_health_checker()
    flags = get_feature_flags()
    state_manager = get_state_manager()
    
    # NFR 2.1: Graceful Degradation - check feature flags
    nfr_2_1 = {
        "status": "operational" if flags.is_enabled("non_core_features_enabled") else "degraded",
        "feature_flags": flags.get_all_flags(),
        "core_checkout_enabled": flags.is_enabled("payment_gateway_enabled")
    }
    
    # NFR 2.2: Fault Detection - check health components
    health = checker.check_all_health()
    nfr_2_2 = {
        "status": health["overall_status"],
        "component_count": len(health["components"]),
        "components": health["components"]
    }
    
    # NFR 2.3: State Preservation - check snapshots
    pending_recoveries = state_manager.get_all_pending_recoveries()
    nfr_2_3 = {
        "status": "operational",
        "pending_recoveries": len(pending_recoveries),
        "recovery_data": pending_recoveries
    }
    
    return NFRVerificationResponse(
        nfr_2_1_graceful_degradation=nfr_2_1,
        nfr_2_2_fault_detection=nfr_2_2,
        nfr_2_3_state_preservation=nfr_2_3
    )
