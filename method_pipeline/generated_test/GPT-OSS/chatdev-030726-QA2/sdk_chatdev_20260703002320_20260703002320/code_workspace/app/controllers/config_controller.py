"""
Configuration management controller.
Provides endpoint to reload settings at runtime for deferred binding.
"""

from fastapi import APIRouter
from app.config.settings import reload_settings
from app.db import get_engine

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/reload")
def reload_config():
    """Reload application settings from environment variables without restart.
    Also clears cached DB engine to apply new DATABASE_URL.
    """
    reload_settings()
    # Clear the cached engine so that next request uses new DB config
    get_engine.cache_clear()
    return {"detail": "Configuration reloaded"}
