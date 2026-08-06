"""
Rate limiter for NFR 1.1 - Limit Event Response
Uses token bucket algorithm with Redis backend
"""
import time
from typing import Optional
import redis
from oms_backend.config import settings


class RateLimiter:
    """
    Rate limiter implementation using token bucket algorithm.
    Satisfies NFR 1.1: Limit Event Response - process events only up to a set maximum rate.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self.redis = redis_client
        self.max_events = settings.rate_limit_max_events
        self.window_seconds = settings.rate_limit_window_seconds
        
    def is_allowed(self, key: str) -> bool:
        """
        Check if an event is allowed for the given key.
        Uses sliding window rate limiting.
        
        Args:
            key: Unique identifier for the rate limit bucket
            
        Returns:
            True if event is allowed, False if rate limit exceeded
        """
        if not settings.enable_rate_limiting:
            return True
            
        current_time = time.time()
        window_key = f"rate_limit:{key}:{int(current_time / self.window_seconds)}"
        
        if self.redis:
            try:
                current_count = self.redis.get(window_key)
                if current_count is None:
                    self.redis.setex(window_key, self.window_seconds, 1)
                    return True
                if int(current_count) >= self.max_events:
                    return False
                self.redis.incr(window_key)
                return True
            except redis.RedisError:
                # Graceful degradation: allow requests if Redis is unavailable
                return True
        else:
            # In-memory fallback (for single-instance deployments)
            return self._in_memory_check(key, current_time)
    
    def _in_memory_check(self, key: str, current_time: float) -> bool:
        """
        In-memory rate limiting fallback.
        
        Args:
            key: Unique identifier for the rate limit bucket
            current_time: Current timestamp
            
        Returns:
            True if event is allowed, False if rate limit exceeded
        """
        window_start = int(current_time / self.window_seconds)
        bucket_key = f"{key}:{window_start}"
        
        if not hasattr(self, '_memory_buckets'):
            self._memory_buckets = {}
            self._memory_timestamps = {}
        
        # Clean old buckets
        cutoff = current_time - (self.window_seconds * 2)
        old_keys = [k for k, t in self._memory_timestamps.items() if t < cutoff]
        for k in old_keys:
            self._memory_buckets.pop(k, None)
            self._memory_timestamps.pop(k, None)
        
        current_count = self._memory_buckets.get(bucket_key, 0)
        if current_count >= self.max_events:
            return False
        
        self._memory_buckets[bucket_key] = current_count + 1
        self._memory_timestamps[bucket_key] = current_time
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()
