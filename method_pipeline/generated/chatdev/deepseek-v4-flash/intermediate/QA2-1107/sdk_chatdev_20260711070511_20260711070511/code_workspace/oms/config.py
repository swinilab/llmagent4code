"""
Application configuration loaded from environment variables with sensible defaults.
"""
import os
from pathlib import Path


class Settings:
    """Central configuration for the OMS backend."""

    # Database
    DATABASE_URL: str = os.getenv(
        "OMS_DATABASE_URL",
        "sqlite:///./oms_data.db",
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("OMS_DB_POOL_SIZE", "5"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("OMS_DB_MAX_OVERFLOW", "10"))

    # Server
    HOST: str = os.getenv("OMS_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("OMS_PORT", "8000"))
    RELOAD: bool = os.getenv("OMS_RELOAD", "false").lower() == "true"

    # Circuit Breaker defaults
    CB_FAILURE_THRESHOLD: int = int(os.getenv("OMS_CB_FAILURE_THRESHOLD", "5"))
    CB_RECOVERY_TIMEOUT: float = float(os.getenv("OMS_CB_RECOVERY_TIMEOUT", "30.0"))
    CB_HALF_OPEN_MAX_CALLS: int = int(os.getenv("OMS_CB_HALF_OPEN_MAX_CALLS", "3"))

    # Retry defaults
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("OMS_RETRY_MAX_ATTEMPTS", "3"))
    RETRY_MIN_WAIT: float = float(os.getenv("OMS_RETRY_MIN_WAIT", "1.0"))
    RETRY_MAX_WAIT: float = float(os.getenv("OMS_RETRY_MAX_WAIT", "10.0"))

    # Degradation
    DEGRADATION_CPU_THRESHOLD: float = float(
        os.getenv("OMS_DEGRADATION_CPU_THRESHOLD", "80.0")
    )
    DEGRADATION_MEM_THRESHOLD: float = float(
        os.getenv("OMS_DEGRADATION_MEM_THRESHOLD", "85.0")
    )

    # Data directory
    DATA_DIR: Path = Path(os.getenv("OMS_DATA_DIR", "./data"))
    OUTBOX_POLL_INTERVAL: float = float(
        os.getenv("OMS_OUTBOX_POLL_INTERVAL", "2.0")
    )


settings = Settings()
