"""
Recommendation service — NON-ESSENTIAL (NFR 2.1).

This service is protected by a circuit breaker. When the circuit is open
or the external service is unavailable, a cached/default fallback is
returned immediately. This ensures that core checkout functionality is
never blocked by recommendation failures.

Reliability/Latency tension: The circuit breaker adds ~1ms overhead in
closed state. When open, it saves 5s (the HTTP timeout) per call. Under
extreme load, this prevents thread pool exhaustion from slow external calls.
"""
from __future__ import annotations

import logging

from app.infrastructure.circuit_breaker import get_recommendations_with_fallback

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for fetching product recommendations.

    This is a NON-ESSENTIAL service. If it fails, the system degrades
    gracefully by returning an empty recommendation list.
    """

    async def get_recommendations(self, customer_id: str) -> dict:
        """
        Fetch recommendations for a customer.

        Returns a dict with 'recommendations' list and 'fallback' flag.
        If the circuit breaker is open, returns empty recommendations.
        """
        result = await get_recommendations_with_fallback(customer_id)
        if result.get("fallback"):
            logger.info(
                "Returning fallback recommendations for customer %s",
                customer_id,
            )
        return result
