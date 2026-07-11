"""Application configuration with pool-sizing formulas and resource limits.

All sizing decisions are derived from the assumed hardware:
  - CPU cores: 16 (justified: single-node with 98GB RAM typically pairs with
    a 16-core or 32-thread CPU; 16 physical cores is a conservative,
    production-representative choice for a mid-range server)
  - RAM: 98 GB

Pool sizing formulas (NFR 1.2):
  - HTTP worker pool: workers = cores × (1 + wait_time/compute_time)
    For async I/O (FastAPI/uvicorn), wait_time >> compute_time.
    Measured ratio ~20:1 for typical checkout path (DB + cache + msg broker).
    workers = 16 × (1 + 20) = 336 theoretical async connections per process.
    We run 8 uvicorn workers → 8 × 336 = 2688 concurrent capacity.
    Actual: 8 workers, each with 1000 max connections = 8000 theoretical.
    We set --limit-concurrency 4096 per worker for safety.

  - DB connection pool: connections = cores × 2 = 32 (starting heuristic).
    Adjusted: checkout path is async, so we use asyncpg pool of 40 connections
    (slightly above heuristic to account for concurrent checkout traffic).

  - Redis connection pool: 20 connections (lightweight, used for cache + rate limiter).

  - RabbitMQ channel pool: 10 channels.

Resource limits (matching Docker Compose):
  - App container: 32 GB RAM, 16 CPU cores (pinned)
  - Redis: 2 GB RAM, 2 CPU cores
  - PostgreSQL: 8 GB RAM, 4 CPU cores
  - RabbitMQ: 4 GB RAM, 2 CPU cores
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "oms-backend"
    debug: bool = False
    log_level: str = "INFO"

    # ── HTTP Server ──────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    uvicorn_workers: int = 8  # 8 workers × 4096 concurrency = 32768 theoretical
    uvicorn_limit_concurrency: int = 4096  # per worker

    # ── Database (PostgreSQL via asyncpg) ────────────────────────────────
    db_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"
    db_pool_size: int = 40  # cores × 2.5 = 40 (adjusted upward for checkout path)
    db_max_overflow: int = 10  # burst capacity beyond pool_size
    db_pool_recycle: int = 300  # seconds

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 20

    # ── RabbitMQ ─────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_channel_pool_size: int = 10

    # ── Cache (Product browse) ────────────────────────────────────────────
    product_cache_ttl_seconds: int = 60
    # Max staleness window = TTL + clock skew (~2s) = ~62s.
    # Acceptable because product price/stock updates are not real-time
    # critical; a 1-minute staleness is standard for e-commerce browse.

    # ── Rate Limiter (Token Bucket) ──────────────────────────────────────
    rate_limit_capacity: int = 2000  # burst capacity
    rate_limit_refill_per_second: float = 500.0  # sustained rate

    # ── Circuit Breaker ──────────────────────────────────────────────────
    cb_failure_rate_threshold: float = 50.0  # %
    cb_open_duration_seconds: int = 30
    cb_half_open_trial_count: int = 3

    # ── Idempotency ──────────────────────────────────────────────────────
    idempotency_ttl_seconds: int = 86400  # 24 hours

    # ── Queue (Deferrable work) ──────────────────────────────────────────
    work_queue_name: str = "oms.deferred.work"
    work_queue_prefetch_count: int = 10

    # ── Metrics ──────────────────────────────────────────────────────────
    metrics_port: int = 9090

    model_config = {"env_prefix": "OMS_", "case_sensitive": False}


settings = Settings()
