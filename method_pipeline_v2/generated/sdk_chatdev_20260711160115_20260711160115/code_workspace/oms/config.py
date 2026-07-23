"""
Configuration via environment variables with Pydantic Settings.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    workers: int = 8  # uvicorn workers (async)
    debug: bool = False

    # Rate Limiting (Token Bucket)
    rate_limit_refill_rate: float = 5000.0  # tokens per second
    rate_limit_burst: int = 10000  # max tokens

    # Circuit Breaker defaults
    cb_failure_threshold: int = 5
    cb_success_threshold: int = 3
    cb_open_duration_ms: int = 30000
    cb_timeout_seconds: float = 5.0  # timeout for downstream calls

    # Cache
    cache_ttl_products: int = 60  # seconds
    cache_ttl_orders: int = 30

    # Queue
    queue_max_size: int = 10000
    queue_worker_count: int = 4

    # Retry
    retry_max_attempts: int = 3
    retry_base_delay_ms: int = 100


settings = Settings()
