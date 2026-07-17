"""Configuration settings for OMS backend."""

import os


class Settings:
    """Application settings loaded from environment variables with defaults."""

    # Database URL (SQLite for local dev, can be overridden)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./oms.db")

    # Feature toggles for graceful degradation
    ENABLE_INVOICE_FEATURE: bool = os.getenv("ENABLE_INVOICE_FEATURE", "true").lower() == "true"
    ENABLE_SHIPPING_FEATURE: bool = os.getenv("ENABLE_SHIPPING_FEATURE", "true").lower() == "true"


settings = Settings()
