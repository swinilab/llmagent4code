"""
Application configuration via environment variables with sensible defaults.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the OMS backend."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    request_timeout_seconds: int = 30

    # Queue
    queue_max_size: int = 1000
    queue_worker_count: int = 4
    queue_poll_interval_seconds: float = 0.1

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 30.0

    # Graceful degradation
    degradation_memory_threshold_mb: int = 512
    degradation_cpu_threshold_percent: float = 90.0

    # State preservation
    state_poll_interval_seconds: float = 5.0

    model_config = {"env_prefix": "OMS_", "env_file": ".env"}


settings = Settings()
