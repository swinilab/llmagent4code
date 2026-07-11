"""
Application configuration via environment variables with sensible defaults.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    debug: bool = False

    # Connection pool sizing (NFR 1.2)
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Circuit breaker defaults (NFR 2.1)
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 30.0

    # Queue admission control (NFR 1.3)
    max_queue_backlog: int = 10_000

    # Retry defaults (NFR 2.2)
    retry_attempts: int = 3
    retry_min_wait: float = 0.5
    retry_max_wait: float = 30.0


settings = Settings()
