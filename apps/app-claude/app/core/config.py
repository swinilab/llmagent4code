"""Effective external configuration for OrderMan.

Every key in this module maps 1:1 to a required environment variable from the
generation contract. The values are read once at import time so that the rest of
the application observes a stable configuration snapshot.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_port: int
    max_in_flight_requests: int
    db_operation_timeout_ms: int
    db_max_attempts: int
    db_retry_backoff_ms: int
    cache_ttl_seconds: int
    enable_test_hooks: bool
    database_url: str

    @property
    def db_operation_timeout_seconds(self) -> float:
        return self.db_operation_timeout_ms / 1000.0

    @property
    def db_retry_backoff_seconds(self) -> float:
        return self.db_retry_backoff_ms / 1000.0

    def as_log_payload(self) -> dict[str, object]:
        """Configuration snapshot emitted at startup.

        The database URL is deliberately excluded because it carries credentials.
        """
        payload = asdict(self)
        payload.pop("database_url", None)
        payload["APP_PORT"] = self.app_port
        payload["MAX_IN_FLIGHT_REQUESTS"] = self.max_in_flight_requests
        payload["DB_OPERATION_TIMEOUT_MS"] = self.db_operation_timeout_ms
        payload["DB_MAX_ATTEMPTS"] = self.db_max_attempts
        payload["DB_RETRY_BACKOFF_MS"] = self.db_retry_backoff_ms
        payload["CACHE_TTL_SECONDS"] = self.cache_ttl_seconds
        payload["ENABLE_TEST_HOOKS"] = self.enable_test_hooks
        return payload


def load_settings() -> Settings:
    return Settings(
        app_port=_int_env("APP_PORT", 8080),
        max_in_flight_requests=_int_env("MAX_IN_FLIGHT_REQUESTS", 10),
        db_operation_timeout_ms=_int_env("DB_OPERATION_TIMEOUT_MS", 1000),
        db_max_attempts=_int_env("DB_MAX_ATTEMPTS", 3),
        db_retry_backoff_ms=_int_env("DB_RETRY_BACKOFF_MS", 100),
        cache_ttl_seconds=_int_env("CACHE_TTL_SECONDS", 5),
        enable_test_hooks=_bool_env("ENABLE_TEST_HOOKS", False),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://orderman:orderman@toxiproxy:8666/orderman",
        ),
    )


settings = load_settings()
