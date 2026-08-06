"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "OMS Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/oms_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis (for caching and rate limiting)
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300  # 5 minutes
    
    # Rate limiting
    rate_limit_max_events: int = 100  # NFR 1.1: max events per second
    rate_limit_window_seconds: int = 1
    
    # Transaction timeout
    transaction_timeout_seconds: int = 30
    
    # Graceful degradation
    enable_caching: bool = True
    enable_rate_limiting: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
