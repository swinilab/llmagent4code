import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application configuration loaded from environment variables.
    Supports deferred binding; each call reads the current environment.
    """
    # Database URL, e.g., sqlite:///./oms.db for local dev
    DATABASE_URL: str = "sqlite:///./oms.db"
    # Service version for API routing
    API_VERSION: str = "v1"
    # Other configurable parameters can be added here

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    """Return a fresh Settings instance, reflecting any env changes.
    This function can be called at runtime to obtain up‑to‑date configuration.
    """
    return Settings()
