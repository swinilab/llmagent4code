"""
Application configuration settings
"""
import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    """
    Application configuration with environment variable support
    """
    host: str = os.getenv("OMS_HOST", "0.0.0.0")
    port: int = int(os.getenv("OMS_PORT", "8080"))
    database_url: str = os.getenv("OMS_DATABASE_URL", "sqlite+aiosqlite:///./oms.db")
    cache_ttl_seconds: int = int(os.getenv("OMS_CACHE_TTL", "300"))
    rate_limit_max_events: int = int(os.getenv("OMS_RATE_LIMIT", "100"))
    rate_limit_window_seconds: int = int(os.getenv("OMS_RATE_LIMIT_WINDOW", "60"))
