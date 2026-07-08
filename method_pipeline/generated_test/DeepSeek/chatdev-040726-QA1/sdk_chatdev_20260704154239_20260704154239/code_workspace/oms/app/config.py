"""
Application configuration loaded from environment variables.
"""
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the OMS backend."""

    app_title: str = "Order Management System"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./oms.db"
    debug: bool = False

    # --- Concurrency (NFR 1.2) ---
    max_workers: int = 8
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # --- Rate limiting (NFR 1.3) ---
    rate_limit_per_minute: int = 100

    # --- Uvicorn workers ---
    uvicorn_workers: int = 4

    model_config = ConfigDict(env_file=".env", env_prefix="OMS_")


settings = Settings()
