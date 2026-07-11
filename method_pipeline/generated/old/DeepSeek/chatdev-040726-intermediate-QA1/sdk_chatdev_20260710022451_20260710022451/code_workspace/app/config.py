"""
Application configuration loaded from environment variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4  # one per core on a 4-core target
    log_level: str = "INFO"

    # ── PostgreSQL ──────────────────────────────────────────────────────
    db_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"
    db_pool_size: int = 20   # see ADR / NFR 1.2 justification
    db_max_overflow: int = 10
    db_pool_timeout: int = 30  # seconds

    # ── Redis ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_product_cache_ttl: int = 60  # seconds

    # ── RabbitMQ ────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    invoice_queue_name: str = "oms.invoice.generation"
    notification_queue_name: str = "oms.notifications"

    # ── Rate Limiter (token bucket) ──────────────────────────────────────
    rate_limit_tokens: int = 200       # max burst
    rate_limit_refill_rate: float = 50.0  # tokens per second
    rate_limit_refill_interval: float = 0.1  # seconds between refill ticks

    # ── Load-test / instrumentation ────────────────────────────────────
    metrics_enabled: bool = True
    metrics_port: int = 9090

    model_config = {"env_prefix": "OMS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
