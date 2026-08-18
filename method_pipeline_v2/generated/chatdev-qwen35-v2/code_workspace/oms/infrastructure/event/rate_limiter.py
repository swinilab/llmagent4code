"""
Rate limiter implementation for NFR 1.1 Limit Event Response
Uses token bucket algorithm to limit event processing rate
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict
from oms.config.app_config import AppConfig

config = AppConfig()

class RateLimiter:
    """
    Singleton rate limiter using token bucket algorithm
    Implements NFR 1.1 via rate limiting tactic
    """
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._max_events = config.rate_limit_max_events
        self._events: Dict[str, list] = {}
    
    @classmethod
    def get_instance(cls) -> 'RateLimiter':
        """Get singleton rate limiter instance"""
        if cls._instance is None:
            cls._instance = RateLimiter()
        return cls._instance
    
    async def is_allowed(self, event_type: str, client_id: str = "default") -> bool:
        """
        Check if event is allowed under rate limit
        Returns True if allowed, False if rate limit exceeded
        """
        key = f"{client_id}:{event_type}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self._window_seconds)
        
        async with self._lock:
            if key not in self._events:
                self._events[key] = []
            
            # Remove expired events
            self._events[key] = [
                ts for ts in self._events[key]
                if ts > window_start
            ]
            
            # Check rate limit
            if len(self._events[key]) >= self._max_events:
                return False
            
            # Record event
            self._events[key].append(now)
            return True
    
    async def get_remaining(self, event_type: str, client_id: str = "default") -> int:
        """Get remaining events allowed in current window"""
        key = f"{client_id}:{event_type}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self._window_seconds)
        
        async with self._lock:
            if key not in self._events:
                return self._max_events
            
            # Count valid events
            valid_events = [
                ts for ts in self._events[key]
                if ts > window_start
            ]
            return max(0, self._max_events - len(valid_events))
    
    async def reset(self, event_type: str, client_id: str = "default") -> None:
        """Reset rate limit for specific event type"""
        key = f"{client_id}:{event_type}"
        async with self._lock:
            if key in self._events:
                del self._events[key]

__all__ = ['RateLimiter']
