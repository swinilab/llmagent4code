from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OMS_",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "oms"
    environment: str = "production"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://oms:oms@postgres:5432/oms"
    redis_url: str = "redis://redis:6379/0"
    event_stream: str = "oms:events"
    event_max_rate: int = Field(default=25, ge=1, le=10_000)
    event_batch_size: int = Field(default=50, ge=1, le=1_000)
    event_poll_interval_seconds: float = Field(default=0.25, gt=0, le=60)
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86_400)
    state_sync_interval_seconds: float = Field(default=60, gt=0, le=86_400)
    dependency_timeout_seconds: float = Field(default=1.5, gt=0, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()

