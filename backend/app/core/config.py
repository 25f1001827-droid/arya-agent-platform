
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Social Media Automation Platform"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered Facebook page automation with regional support"

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    REGION: str = Field(default="US", env="REGION")  # US or UK

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ENCRYPTION_KEY: str = Field(..., env="ENCRYPTION_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # AI APIs
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")

    # Facebook API
    FACEBOOK_APP_ID: str = Field(..., env="FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET: str = Field(..., env="FACEBOOK_APP_SECRET")
    FACEBOOK_API_VERSION: str = "v19.0"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Regional Settings
    TIMEZONE_US: str = "America/New_York"
    TIMEZONE_UK: str = "Europe/London"

    # Content Generation
    DEFAULT_IMAGE_SIZE: str = "1024x1024"
    MAX_CAPTION_LENGTH: int = 2200
    MIN_CAPTION_LENGTH: int = 50

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://yourdomain.com"
    ]

    # Monitoring & Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

