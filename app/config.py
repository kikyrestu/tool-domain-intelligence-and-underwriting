"""
Application configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    # Database — bisa pakai DATABASE_URL langsung (legacy)
    # atau pakai field terpisah (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    DATABASE_URL: str = ""

    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_SSL: bool = True  # set False untuk koneksi lokal tanpa SSL

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        """Rakit DATABASE_URL dari field terpisah jika DATABASE_URL belum diset."""
        if not self.DATABASE_URL and self.DB_HOST and self.DB_NAME:
            ssl_param = "?ssl=require" if self.DB_SSL else ""
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}{ssl_param}"
            )
        if not self.DATABASE_URL:
            raise ValueError(
                "Set DATABASE_URL atau DB_HOST + DB_NAME + DB_USER + DB_PASSWORD di .env"
            )
        return self

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

    # Scheduler
    STARRED_RECHECK_HOURS: float = 6.0

    # 2captcha — optional, only used if Playwright+Stealth fails on Cloudflare Turnstile
    TWOCAPTCHA_API_KEY: str = ""

    # ── Scraping API Providers ─────────────────────────────────────────────
    # Semua support comma-separated multi-key (round-robin per provider).
    # Provider dirotasi berurutan: ZenRows → ScraperAPI → Scrapingbee → Crawlbase
    # Tiap provider: basic → js_render → antibot (escalate kalau kena challenge)

    # ZenRows (scraperapi.com) — https://zenrows.com
    ZENROWS_API_KEY: str = ""   # single key (legacy, masih supported)
    ZENROWS_API_KEYS: str = ""  # preferred: key1,key2,key3,...

    # ScraperAPI (scraperapi.com) — https://scraperapi.com
    SCRAPERAPI_KEYS: str = ""   # key1,key2,...

    # Scrapingbee (scrapingbee.com) — https://scrapingbee.com
    SCRAPINGBEE_KEYS: str = ""  # key1,key2,...

    # Crawlbase / ProxyCrawl (crawlbase.com) — https://crawlbase.com
    CRAWLBASE_KEYS: str = ""     # normal token (1 credit) key1,key2,...
    CRAWLBASE_JS_KEYS: str = ""  # JS token (5 credits, headless+residential) key1,key2,...

    # ScrapeGraphAI (scrapegraphai.com) — AI-based scraper, last resort for tricky pages
    SCRAPEGRAPHAI_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
