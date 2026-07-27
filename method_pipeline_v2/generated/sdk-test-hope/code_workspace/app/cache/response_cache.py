from aiocache import Cache
from typing import Callable, Any

# Simple in-memory cache for response data (NFR 1.1)
response_cache = Cache(Cache.MEMORY)

async def get_or_set_cached_product_list(loader: Callable[[], Any]):
    """Retrieve product list from cache or compute via loader and store it.
    Used for NFR 1.1 to reduce latency on frequent product list reads.
    """
    key = "product_list"
    value = await response_cache.get(key)
    if value is None:
        value = await loader()
        await response_cache.set(key, value)
    return value
