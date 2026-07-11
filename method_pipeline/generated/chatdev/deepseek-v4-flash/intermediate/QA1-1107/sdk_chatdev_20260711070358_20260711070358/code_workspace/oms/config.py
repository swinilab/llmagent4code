"""
Configuration for the Order Management System.
Uses pydantic-settings for environment-based configuration.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Order Management System"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4  # Matches typical multi-core CPU

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://oms:oms@localhost:5432/oms"
    database_pool_size: int = 20   # Bounded pool: 20 connections
    database_max_overflow: int = 10  # Additional overflow connections
    database_pool_timeout: int = 30  # Seconds to wait for a connection

    # Redis (Cache + Rate Limiter + Task Queue)
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10

    # Rate Limiting
    # Capacity and refill rate tuned for 2,000 concurrent users (NFR 1.2).
    # With 200 tokens/s refill and 500 burst capacity, the limiter allows
    # ~200 POST requests per second sustained, which is well above the
    # expected checkout throughput at 2,000 concurrent users with think times.
    rate_limit_tokens: int = 500     # Token bucket capacity (burst allowance)
    rate_limit_refill_rate: float = 200.0  # Tokens per second (sustained rate)
    rate_limit_refill_interval: float = 1.0  # Seconds between refills

    # Cache
    product_cache_ttl: int = 60  # Seconds
    product_cache_max_size: int = 10000

    # Task Queue (RQ)
    task_queue_name: str = "oms_tasks"
    task_worker_count: int = 2

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
