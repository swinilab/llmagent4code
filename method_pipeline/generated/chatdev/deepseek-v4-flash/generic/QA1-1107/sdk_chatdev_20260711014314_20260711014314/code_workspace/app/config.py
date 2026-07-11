"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the OMS backend."""

    # Application
    app_name: str = "Order Management System"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Task Queue (Celery)
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Background processing
    background_queue_maxsize: int = 1000
    background_workers: int = 4

    # Pricing defaults (configurable per deployment)
    tax_rate: str = "0.08"
    shipping_cost: str = "9.99"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
