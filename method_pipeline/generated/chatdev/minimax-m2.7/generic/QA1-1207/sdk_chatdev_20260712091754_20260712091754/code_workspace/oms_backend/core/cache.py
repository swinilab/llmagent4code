"""
In-memory LRU cache and Redis cache utilities.
"""
from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import Any, Callable, TypeVar

from oms_backend.core.config import get_settings

T = TypeVar("T")


class LRUCache:
    """
    Simple thread-unsafe LRU cache for a single worker process.
    For multi-worker: use Redis cache (see RedisCache below).
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        val, expires = self._store.get(key, (None, 0))
        if val is None:
            return None
        if expires > 0 and __import__("time").time() > expires:
            del self._store[key]
            return None
        # Move to end (most recently used)
        self._store.move_to_end(key)
        return val

    def set(self, key: str, value: Any, ttl_seconds: int = 0) -> None:
        expires = __import__("time").time() + ttl_seconds if ttl_seconds > 0 else 0
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, expires)
        if len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix."""
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]


# Global LRU cache (worker-local)
_product_cache = LRUCache(max_size=5000)


def get_product_cache() -> LRUCache:
    return _product_cache
