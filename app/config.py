"""Application configuration settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


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

    # Job Title Pre-Filtering (to reduce AI API calls)
    # Jobs with titles containing these keywords will be auto-rejected (LOW score) without AI
    # Comma-separated list, case-insensitive
    job_title_exclude_keywords: str = "senior,sr.,experienced,architect,staff,team lead,manager,lead,principal,director,vp,head of,chief"
    # Jobs with titles containing these keywords will be auto-accepted for AI analysis
    # Leave empty to analyze all non-excluded jobs
    job_title_include_keywords: str = ""
    # Jobs containing these keywords will always trigger notification regardless of match score
    # Comma-separated list, case-insensitive
    job_title_must_notify_keywords: str = "junior,entry-level,entry level,intern,graduate"
    # Enable/disable pre-filtering (set to false to always use AI)
    job_prefilter_enabled: bool = True

    # Storage
    storage_path: str = "./storage"
    cv_storage_path: str = "./storage/cvs"
    temp_storage_path: str = "./storage/temp"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    def get_exclude_keywords(self) -> List[str]:
        """Parse exclude keywords into a list"""
        if not self.job_title_exclude_keywords:
            return []
        return [k.strip().lower() for k in self.job_title_exclude_keywords.split(",") if k.strip()]

    def get_include_keywords(self) -> List[str]:
        """Parse include keywords into a list"""
        if not self.job_title_include_keywords:
            return []
        return [k.strip().lower() for k in self.job_title_include_keywords.split(",") if k.strip()]

    def get_must_notify_keywords(self) -> List[str]:
        """Parse must-notify keywords into a list"""
        if not self.job_title_must_notify_keywords:
            return []
        return [k.strip().lower() for k in self.job_title_must_notify_keywords.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
