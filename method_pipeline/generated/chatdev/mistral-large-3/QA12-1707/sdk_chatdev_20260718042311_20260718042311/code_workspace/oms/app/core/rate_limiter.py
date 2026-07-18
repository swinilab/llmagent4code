"""
Rate limiter for graceful degradation.
"""
from collections import defaultdict
import time


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = defaultdict(list)

    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        now = time.time()
        # Remove old requests
        self.request_counts[client_id] = [
            t for t in self.request_counts[client_id] if now - t < self.window_seconds
        ]
        # Check if limit exceeded
        if len(self.request_counts[client_id]) >= self.max_requests:
            return True
        # Add current request
        self.request_counts[client_id].append(now)
        return False


rate_limiter = RateLimiter(max_requests=100, window_seconds=60)