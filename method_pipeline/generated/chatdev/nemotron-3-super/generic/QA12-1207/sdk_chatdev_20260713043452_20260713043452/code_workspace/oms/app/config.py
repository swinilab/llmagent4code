from pydantic_settings import BaseSettings
from pydantic import PostgresDsn
from typing import Optional, List, Union
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "Order Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "oms")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DB_ECHO: bool = os.getenv("DB_ECHO", "False") == "True"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # Security (not used now but placeholder)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Feature flags (for graceful degradation)
    FEATURE_PAYMENT_PROCESSING_ENABLED: bool = os.getenv("FEATURE_PAYMENT_PROCESSING_ENABLED", "True") == "True"
    FEATURE_INVOICE_GENERATION_ENABLED: bool = os.getenv("FEATURE_INVOICE_GENERATION_ENABLED", "True") == "True"
    FEATURE_ORDER_SHIPPING_ENABLED: bool = os.getenv("FEATURE_ORDER_SHIPPING_ENABLED", "True") == "True"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()