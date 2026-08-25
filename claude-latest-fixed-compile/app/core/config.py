"""Central runtime configuration. All tunables are environment-overridable."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OMS Backend"
    api_v1_prefix: str = "/api/v1"

    # Primary store (NFR 1.2 - replication primary)
    database_url: str = "postgresql+psycopg://oms:oms@postgres-primary:5432/oms"
    # Read replica (NFR 1.2 - data replication)
    database_replica_url: str = "postgresql+psycopg://oms:oms@postgres-replica:5432/oms"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    # NFR 2.1 - timeout-based exception detection at the DB boundary
    db_statement_timeout_ms: int = 3000

    # Cache (NFR 1.2 - caching)
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 60
    # NFR 2.1 - timeout tactic on the cache dependency
    redis_timeout_seconds: float = 0.25

    # NFR 1.1 - limit event response (token bucket)
    rate_limit_capacity: int = 100
    rate_limit_refill_per_second: float = 50.0

    # NFR 2.2 - graceful degradation (circuit breaker around non-critical deps)
    breaker_fail_max: int = 5
    breaker_reset_timeout_seconds: int = 30

    # NFR 2.3 - state resynchronization sweep
    resync_interval_seconds: int = 15
    resync_drift_tolerance: int = 0

    supported_currencies: tuple[str, ...] = ("USD", "VND", "EUR")

    model_config = {"env_prefix": "OMS_", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
