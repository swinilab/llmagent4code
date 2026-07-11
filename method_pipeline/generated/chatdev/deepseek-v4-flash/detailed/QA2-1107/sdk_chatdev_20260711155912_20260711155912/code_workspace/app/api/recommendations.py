"""
Recommendation API endpoint — NON-ESSENTIAL (NFR 2.1).

Protected by a circuit breaker. When the external service is unavailable,
returns a cached fallback immediately.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("/{customer_id}")
async def get_recommendations(customer_id: str) -> dict:
    """
    Fetch product recommendations for a customer.

    This is a NON-ESSENTIAL endpoint. If the recommendation service
    is unavailable, a fallback (empty list) is returned immediately.
    """
    service = RecommendationService()
    return await service.get_recommendations(customer_id)
