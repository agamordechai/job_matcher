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

    # RapidAPI (JSearch for job fetching)
    rapidapi_key: str = ""
    rapidapi_host: str = "jsearch.p.rapidapi.com"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notification_email: str = ""

    # Scheduler
    fetch_interval_minutes: int = 30
    timezone: str = "Asia/Jerusalem"

    # Job Search Filters (Defaults - POC: US Remote Jobs)
    search_keywords: str = "Software Engineer,Backend Developer,Data Engineer"
    search_location: str = "United States"
    search_job_type: str = ""  # Empty = no filter
    search_experience_level: str = ""  # Empty = no filter
    search_remote_only: bool = True  # Remote jobs for POC
    search_date_posted: str = "month"
    search_max_pages: int = 2

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

