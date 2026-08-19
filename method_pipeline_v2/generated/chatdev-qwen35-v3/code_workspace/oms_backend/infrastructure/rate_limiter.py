"""
Rate limiter for NFR 1.1 (Limit Event Response)
Implements token bucket algorithm to limit event processing rate
"""
import time
from collections import defaultdict
from typing import Dict
from oms_backend.config.settings import get_settings

settings = get_settings()


class RateLimiter:
    """
    Token bucket rate limiter for limiting event processing rate.
    Implements NFR 1.1: process events only up to a set maximum rate.
    
    Tactic: Performance > Limit Event Response
    """
    
    def __init__(self, max_events_per_second: int = None):
        self.max_rate = max_events_per_second or settings.max_events_per_second
        self.tokens_per_second = self.max_rate
        self.max_tokens = self.max_rate
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": self.max_tokens,
            "last_update": time.time()
        })
    
    def _refill_tokens(self, key: str) -> None:
        """Refill tokens based on elapsed time"""
        bucket = self.buckets[key]
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        # Add tokens based on elapsed time
        bucket["tokens"] = min(
            self.max_tokens,
            bucket["tokens"] + elapsed * self.tokens_per_second
        )
        bucket["last_update"] = now
    
    def allow_request(self, key: str = "global") -> bool:
        """
        Check if a request should be allowed.
        Returns True if allowed, False if rate limited.
        """
        self._refill_tokens(key)
        
        if self.buckets[key]["tokens"] >= 1:
            self.buckets[key]["tokens"] -= 1
            return True
        return False
    
    def get_remaining_tokens(self, key: str = "global") -> float:
        """Get remaining tokens for a key"""
        self._refill_tokens(key)
        return self.buckets[key]["tokens"]
    
    def reset(self, key: str = None) -> None:
        """Reset rate limiter state"""
        if key:
            self.buckets.pop(key, None)
        else:
            self.buckets.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()
