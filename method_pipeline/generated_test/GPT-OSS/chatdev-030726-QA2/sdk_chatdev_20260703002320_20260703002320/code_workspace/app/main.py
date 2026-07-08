"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.db import Base, engine

# Load settings lazily
settings = get_settings()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, version="1.0.0")
app.include_router(api_router)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "OMS Backend is running"}
