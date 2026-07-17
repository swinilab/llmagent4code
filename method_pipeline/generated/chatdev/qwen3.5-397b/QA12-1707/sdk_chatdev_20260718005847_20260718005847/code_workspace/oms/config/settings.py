"""
Configuration module for OMS application.
Handles environment variables and application settings.
"""

import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./oms.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8003"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    
    # Performance
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "100"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Graceful degradation
    ENABLE_DEGRADED_MODE: bool = os.getenv("ENABLE_DEGRADED_MODE", "true").lower() == "true"
    MAX_PENDING_ORDERS: int = int(os.getenv("MAX_PENDING_ORDERS", "1000"))
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the database connection URL."""
        return cls.DATABASE_URL
    
    @classmethod
    def is_debug(cls) -> bool:
        """Check if debug mode is enabled."""
        return os.getenv("DEBUG", "false").lower() == "true"


config = Config()
