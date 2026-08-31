"""Application entrypoint - wiring, lifespan, error handling, OpenAPI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.v1 import ops
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import DomainError
from app.core.middleware import ExceptionDetectionMiddleware, RateLimitMiddleware
from app.infra.cache import EntityCache
from app.infra.database import primary_engine
from app.infra.rate_limiter import TokenBucketRateLimiter
from app.infra.resync import StateResynchronizer
from app.repositories.schema import Base

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("oms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=primary_engine)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis
    app.state.cache = EntityCache(redis)
    app.state.rate_limiter = TokenBucketRateLimiter(redis)
    app.state.metrics = {"throttled": 0, "exceptions_detected": 0, "timeouts": 0}

    app.state.resynchronizer = StateResynchronizer(app.state.cache)
    app.state.resynchronizer.start()  # NFR 2.3 background sweep
    logger.info("OMS started; resync every %ss", settings.resync_interval_seconds)

    try:
        yield
    finally:
        await app.state.resynchronizer.stop()
        await redis.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Backend-only Order Management System.\n\n"
        "Workflow: place -> accept -> invoice -> pay -> verify -> ship -> close."
    ),
    lifespan=lifespan,
    openapi_url="/openapi.json",
    docs_url="/docs",
)

# Order matters: detection wraps the limiter so a throttle is still traced.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ExceptionDetectionMiddleware)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Body/field constraint violations answer 400, not FastAPI's default 422.

    The BVA/EP harness asserts 400 for every invalid-partition case, so this
    mapping is part of the contract rather than cosmetic.
    """
    return JSONResponse(
        status_code=400,
        content={
            "code": "validation_error",
            "message": "request failed field constraint validation",
            "detail": {
                "violations": [
                    {"field": ".".join(str(p) for p in err["loc"][1:]), "error": err["msg"]}
                    for err in exc.errors()
                ]
            },
        },
    )


app.include_router(ops.router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
