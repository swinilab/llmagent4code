"""
Application settings and configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Rate limiting for NFR 1.1
    max_events_per_second: int = 100
    
    # Timeout settings for NFR 2.1
    default_timeout_seconds: int = 30
    db_timeout_seconds: int = 10
    
    # Retry settings for NFR 2.2
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # State sync interval for NFR 2.3 (seconds)
    state_sync_interval: int = 60
    
    # Enable fault injection for testing
    fault_injection_enabled: bool = False
    fault_type: Optional[str] = None  # "timeout", "error", "slow"
    fault_duration_ms: int = 5000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings singleton"""
    return Settings()
