from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "ChatDev API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()