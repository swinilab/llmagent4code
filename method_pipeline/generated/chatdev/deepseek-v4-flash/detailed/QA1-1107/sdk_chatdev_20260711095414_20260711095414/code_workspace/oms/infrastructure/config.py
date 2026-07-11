"""
Configuration loaded from environment / .env file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4  # matches assumed 8-core CPU; see ADR

    # ── PostgreSQL ───────────────────────────────────────────────────────
    db_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"
    db_pool_size: int = 16  # cores × 2 = 8×2 = 16; see NFR 1.2 derivation
    db_max_overflow: int = 8  # burst headroom

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    product_cache_ttl_seconds: int = 60  # max staleness window = 60 s
    idempotency_ttl_seconds: int = 3600  # 1 hour

    # ── RabbitMQ ────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    queue_name: str = "oms_deferred_tasks"
    consumer_concurrency: int = 8  # one per core

    # ── Rate Limiter (token bucket) ──────────────────────────────────────
    rate_limit_capacity: int = 5000  # burst capacity
    rate_limit_refill_per_second: int = 1000  # sustained refill rate

    # ── Circuit Breaker ─────────────────────────────────────────────────
    cb_failure_threshold: float = 0.5  # 50% failure rate opens
    cb_recovery_timeout: float = 30.0  # seconds before half-open
    cb_half_open_max_calls: int = 3

    # ── Metrics ─────────────────────────────────────────────────────────
    metrics_port: int = 9090

    model_config = {"env_prefix": "OMS_", "env_file": ".env"}


settings = Settings()
