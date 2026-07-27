from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.db.connection_pool import get_engine
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from sqlalchemy.exc import OperationalError

health_router = APIRouter()

@health_router.get('/ready')
async def readiness() -> JSONResponse:
    # Simple readiness check: can we get a DB connection?
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute('SELECT 1')
        return JSONResponse(content={'status': 'ready'})
    except Exception:
        return JSONResponse(content={'status': 'unready'}, status_code=503)

@health_router.get('/live')
async def liveness() -> JSONResponse:
    return JSONResponse(content={'status': 'alive'})
