"""
Application configuration loaded from environment variables / .env file.
Supports NFR 2.3 (Deferred Binding) — all settings are changeable at
runtime via environment variables without restarting the application
(when using a reload-capable server like uvicorn --reload).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with deferred binding via env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api/v1"
    openapi_title: str = "OMS - Order Management System"
    openapi_version: str = "1.0.0"
    openapi_description: str = "Production-grade e-commerce Order Management System backend."


settings = Settings()
