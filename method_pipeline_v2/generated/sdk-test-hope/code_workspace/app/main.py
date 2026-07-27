from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from app.controllers import router as api_router
from app.health.liveness import health_router
from decimal import Decimal
import datetime

def create_app() -> FastAPI:
    app = FastAPI(
        title='OMS Backend',
        json_encoder=lambda obj: str(obj) if isinstance(obj, (Decimal, datetime.datetime, datetime.date)) else jsonable_encoder(obj)
    )
    app.include_router(api_router)
    app.include_router(health_router, prefix='/health')
    return app

app = create_app()
