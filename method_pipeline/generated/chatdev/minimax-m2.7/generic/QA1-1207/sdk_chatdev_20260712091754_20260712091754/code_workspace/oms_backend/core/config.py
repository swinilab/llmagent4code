"""
Core infrastructure: configuration loader, database connection, cache, and rate limiting.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────────────────
# Config Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str
    name: str
    min_pool_size: int = 20
    max_pool_size: int = 100
    pool_timeout: int = 30

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    host: str
    port: int
    db: int = 0
    password: str = ""

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    debug: bool = False
    log_level: str = "info"
    cors_origins: list[str] = []


class RateLimitingConfig(BaseModel):
    enabled: bool = True
    per_customer_rpm: int = 100
    global_rpm: int = 10000
    burst: int = 200


class CacheConfig(BaseModel):
    product_ttl_seconds: int = 300
    order_ttl_seconds: int = 60


class QueueConfig(BaseModel):
    redis_url: str
    max_jobs: int = 1000
    job_timeout_seconds: int = 60
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


class PaymentGatewayConfig(BaseModel):
    enabled: bool = True
    api_key: str = ""
    api_secret: str = ""
    callback_url: str = ""
    timeout_seconds: int = 30
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 30


class TaxConfig(BaseModel):
    default_rate: str = "0.0825"


class Settings(BaseModel):
    database: DatabaseConfig
    redis: RedisConfig
    app: AppConfig
    rate_limiting: RateLimitingConfig = RateLimitingConfig()
    cache: CacheConfig = CacheConfig()
    queue: QueueConfig
    payment_gateway: PaymentGatewayConfig = PaymentGatewayConfig()
    tax: TaxConfig = TaxConfig()


# ─────────────────────────────────────────────────────────────────────────────
# Config Loader (singleton)
# ─────────────────────────────────────────────────────────────────────────────

def _find_config_path() -> Path:
    """Search for config.yaml in project-standard locations."""
    # env var takes priority
    env_path = os.getenv("OMS_CONFIG")
    if env_path:
        return Path(env_path)

    # Look relative to this file's directory (project root)
    # oms_backend/core/config.py → project root is oms_backend/
    module_root = Path(__file__).parent.parent
    candidate = module_root / "config.yaml"
    if candidate.exists():
        return candidate

    # Fallback to cwd
    cwd_candidate = Path("config.yaml")
    if cwd_candidate.exists():
        return cwd_candidate

    # Return default path (will fail with readable error)
    return module_root / "config.yaml"


_CONFIG_PATH = _find_config_path()


def load_config(path: Path | None = None) -> Settings:
    """Load YAML config, validate with Pydantic, and return Settings singleton."""
    target = path or _CONFIG_PATH
    raw = yaml.safe_load(target.read_text())
    return Settings.model_validate(raw)


# Global singleton (lazy-loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reload_settings(path: Path | None = None) -> Settings:
    """Force reload from disk (useful for testing or hot-reload)."""
    global _settings
    _settings = load_config(path)
    return _settings
