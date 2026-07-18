"""
Request logging middleware.
"""
import time
import structlog
from fastapi import Request

logger = structlog.get_logger()


async def log_requests(request: Request, call_next):
    """Log incoming requests and responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "Request processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time
    )
    return response