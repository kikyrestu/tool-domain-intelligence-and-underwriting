"""
Application configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/domainiq"

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production"
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD: str = "admin"

    # Proxy
    PROXY_FILE: str = "proxies.txt"
    PROXY_ENABLED: bool = True

    # Scoring — thresholds no longer used for labels (context-based now)
    # Kept for backward compatibility
    SCORE_BUY_THRESHOLD: int = 80
    SCORE_DISCARD_THRESHOLD: int = 40

    # Rate limiting
    CRAWL_DELAY_SECONDS: float = 2.0
    RDAP_DELAY_SECONDS: float = 1.0
    WAYBACK_DELAY_SECONDS: float = 1.0

    # Limits
    MAX_CANDIDATES_PER_CRAWL: int = 500
    WAYBACK_SAMPLE_SIZE: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
