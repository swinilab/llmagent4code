"""Simple in‑memory async cache used for read‑only data (e.g., product list).

Leverages aiocache for demonstration; could be swapped for Redis in production.
"""

import asyncio
from aiocache import Cache

class ResponseCache:
    def __init__(self):
        self._cache = Cache(Cache.MEMORY, ttl=60)  # 60 s TTL – balances freshness vs latency

    async def get(self, key: str):
        return await self._cache.get(key)

    async def set(self, key: str, value, ttl: int = 60):
        await self._cache.set(key, value, ttl=ttl)
