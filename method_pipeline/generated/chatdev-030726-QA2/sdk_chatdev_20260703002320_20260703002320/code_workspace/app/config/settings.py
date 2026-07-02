"""
Application configuration and settings.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
from functools import lru_cache

class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.
    Supports deferred binding – changes to env vars affect the app on next request without restart.
    """
    APP_NAME: str = Field(default="OMS Backend", env="APP_NAME")
    DEBUG: bool = Field(default=False, env="DEBUG")
    DATABASE_URL: str = Field(default="sqlite:///./oms.db", env="DATABASE_URL")
    # API versioning
    API_V1_STR: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Cached settings instance with ability to reload at runtime
@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance. Use reload_settings() to refresh."""
    return Settings()

def reload_settings() -> Settings:
    """Force a reload of settings from current environment variables."""
    get_settings.cache_clear()
    return get_settings()
