"""
Application configuration using pydantic-settings.

All settings are environment-variable driven with sensible production defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration for the OMS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OMS_",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "OMS Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Queue / Backpressure ─────────────────────────────────────
    queue_max_size: int = 500
    queue_worker_count: int = 4
    queue_timeout_seconds: float = 5.0

    # ── Circuit Breaker ──────────────────────────────────────────
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 30.0
    cb_half_open_max_calls: int = 3

    # ── Graceful Degradation ─────────────────────────────────────
    degradation_cpu_threshold: float = 85.0  # percent
    degradation_memory_threshold: float = 85.0  # percent
    degradation_check_interval: float = 10.0  # seconds

    # ── Tax ──────────────────────────────────────────────────────
    default_tax_rate: float = 0.20  # 20 %
    default_currency: str = "USD"


settings = Settings()