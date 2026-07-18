"""
Centralised application configuration loaded from environment variables.

ADR-001: Use pydantic-settings for typed, validated configuration.
  Decision: pydantic-settings with .env file support.
  Context: NFR 2.3 (State Preservation) — deterministic config reduces crash-surface.
  Alternatives: (a) os.environ directly — no validation; (b) python-decouple — less type-safe.
  Consequences: Adds pydantic dependency but gives strict validation at startup.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Server ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    log_level: str = "info"

    # ── Database ───────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # ── Rate Limiting (NFR 1.3) ────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_requests_per_second: int = 100
    rate_limit_burst_size: int = 200

    # ── Circuit Breaker (NFR 2.1, 2.2) ────────────────────
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: int = 30

    # ── Work dirs ──────────────────────────────────────────
    data_dir: Path = Path("./data")

    @property
    def database_url_sync(self) -> str:
        """Return sync-compatible URL for migration tooling."""
        return self.database_url.replace("+aiosqlite", "").replace("sqlite+aiosqlite", "sqlite")


settings = Settings()
