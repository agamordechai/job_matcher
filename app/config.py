"""Application configuration settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "Job Matcher"
    environment: str = "development"
    port: int = 8000

    # Database
    database_url: str

    # Redis
    redis_url: str

    # AI Service
    anthropic_api_key: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notification_email: str = ""

    # Scheduler
    fetch_interval_minutes: int = 60
    timezone: str = "UTC"

    # Storage
    storage_path: str = "./storage"
    cv_storage_path: str = "./storage/cvs"
    temp_storage_path: str = "./storage/temp"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

