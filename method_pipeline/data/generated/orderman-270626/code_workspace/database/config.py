"""
Database configuration for the Order Management System.
Uses SQLite for local deployment with async support.
"""
import os

# Database URL - SQLite for local deployment
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./order_management.db"
)

# Connection pool settings
POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "1800"))

# Feature flags for runtime configuration
FEATURE_FLAGS = {
    "enable_analytics": os.environ.get("FEATURE_ANALYTICS", "true").lower() == "true",
    "enable_recommendations": os.environ.get("FEATURE_RECOMMENDATIONS", "true").lower() == "true",
    "enable_heavy_logging": os.environ.get("FEATURE_HEAVY_LOGGING", "false").lower() == "true",
}

# Cache settings
CACHE_EXPIRATION_SECONDS = int(os.environ.get("CACHE_EXPIRATION", "300"))
