"""
Application configuration via environment variables with Pydantic Settings.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — loaded from .env or environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "oms"
    DB_PASSWORD: str = "oms_secret"
    DB_NAME: str = "oms_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800  # seconds

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Server ────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1  # single-node; keep 1 for state consistency

    # ── Circuit Breaker (non-essential services) ────────────────────────────
    RECOMMENDATION_URL: str = "http://localhost:9001/recommend"
    CB_FAILURE_THRESHOLD: int = 3
    CB_RECOVERY_TIMEOUT: float = 30.0  # seconds before half-open

    # ── Retry ──────────────────────────────────────────────────────────────
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_MIN_WAIT: float = 0.5  # seconds
    RETRY_MAX_WAIT: float = 5.0

    # ── Outbox ─────────────────────────────────────────────────────────────
    OUTBOX_POLL_INTERVAL: float = 2.0  # seconds
    OUTBOX_BATCH_SIZE: int = 50

    # ── Resource limits (target: 2 vCPU, 4 GB RAM) ─────────────────────────
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT: float = 30.0


settings = Settings()
