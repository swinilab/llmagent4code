"""
Application configuration via environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OMS Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "sqlite:///./oms.db"
    database_echo: bool = False

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 30.0
    circuit_breaker_half_open_max_requests: int = 3

    state_snapshot_interval_seconds: int = 60
    event_log_max_size: int = 10_000

    class Config:
        env_prefix = "OMS_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()
