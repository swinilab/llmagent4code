"""
Server entry point for OMS application
"""
import uvicorn
from oms.config.app_config import AppConfig
from oms.infrastructure.database import init_db, get_async_session
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.event.rate_limiter import RateLimiter
from oms.app import create_app

config = AppConfig()

def run():
    """
    Initialize database, cache, rate limiter and start the FastAPI server
    """
    import asyncio
    
    async def setup():
        await init_db()
        MemoryCache.get_instance()
        RateLimiter.get_instance()
    
    asyncio.run(setup())
    
    uvicorn.run(
        "oms.app:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run()
