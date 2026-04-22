"""Core configuration settings for the email outreach system."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Google OAuth2
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="", alias="GOOGLE_REDIRECT_URI")

    # Backend
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # Email Settings
    est_timezone: str = Field(default="America/New_York", alias="EST_TIMEZONE")
    send_window_start: int = Field(default=9, alias="SEND_WINDOW_START")
    send_window_end: int = Field(default=17, alias="SEND_WINDOW_END")
    skip_weekends: bool = Field(default=True, alias="SKIP_WEEKENDS")

    # Rate Limits
    max_emails_per_day: int = Field(default=12, alias="MAX_EMAILS_PER_DAY")
    max_emails_per_hour: int = Field(default=3, alias="MAX_EMAILS_PER_HOUR")
    min_delay_between_emails: int = Field(default=600, alias="MIN_DELAY_BETWEEN_EMAILS")
    random_delay_range: int = Field(default=300, alias="RANDOM_DELAY_RANGE")
    occasional_pause_after_emails: int = Field(default=3, alias="OCCASIONAL_PAUSE_AFTER_EMAILS")
    occasional_pause_duration: int = Field(default=1800, alias="OCCASIONAL_PAUSE_DURATION")

    # Follow-up Timing
    followup1_days: int = Field(default=3, alias="FOLLOWUP1_DAYS")
    followup2_days: int = Field(default=6, alias="FOLLOWUP2_DAYS")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
