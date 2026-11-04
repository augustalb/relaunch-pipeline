"""Central configuration.

Every knob lives here and is loaded from environment variables / `.env`
(see `.env.example`). Nothing else in the code base reads `os.environ`
directly, so the operator always has one place to look.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("PIPELINE_ENV_FILE", str(PROJECT_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------ general
    ENV: Literal["dev", "prod", "test"] = "dev"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DATABASE_URL: str = ""  # empty -> sqlite in DATA_DIR
    TIMEZONE: str = "Europe/Berlin"

    # ----------------------------------------------------------------- business
    INDUSTRY: str = "fahrschulen"
    REGION_CITIES_FILE: Path = PROJECT_ROOT / "config" / "cities_nrw.txt"
    SENDER_NAME: str = "Vorname Nachname"
    SENDER_TITLE: str = "Webdesign"
    SENDER_ADDRESS: str = "Musterstraße 1, 12345 Musterstadt"
    SENDER_PHONE: str = ""
    REPLY_TO_EMAIL: str = "auguyoga@gmail.com"  # receives replies only, never sends
    SETUP_PRICE: int = 390
    MONTHLY_PRICE: int = 30
    PREVIEW_DOMAIN: str = "preview.example.de"
    PREVIEW_BASE_URL: str = ""  # defaults to https://{PREVIEW_DOMAIN}
    BRAND_NAME: str = ""  # optional brand shown in the preview banner, falls back to SENDER_NAME

    # ---------------------------------------------------------------- discovery
    GOOGLE_PLACES_API_KEY: str = ""
    PLACES_MAX_REQUESTS_PER_RUN: int = 60
    PLACES_PAGES_PER_QUERY: int = 3
    PLACES_CACHE_DAYS: int = 30  # Google Maps Platform ToS: cache most content <= 30 days
    CHAIN_MIN_LOCATIONS: int = 3  # same domain at >= N places -> treated as chain

    # ------------------------------------------------------------------ scoring
    PAGESPEED_API_KEY: str = ""
    PAGESPEED_MAX_REQUESTS_PER_RUN: int = 100
    SCORE_THRESHOLD: int = 55  # >= threshold -> qualified
    HTTP_TIMEOUT_SECONDS: float = 20.0
    USER_AGENT: str = "Mozilla/5.0 (compatible; RelaunchPipeline/0.1; +https://example.de/bot)"

    # ------------------------------------------------------------------ contact
    MILLIONVERIFIER_API_KEY: str = ""
    REQUIRE_VERIFIED_EMAIL: bool = True
    MX_CHECK: bool = True

    # --------------------------------------------------------------- extraction
    EXTRACT_MAX_PAGES: int = 8
    EXTRACT_USE_PLAYWRIGHT: bool = True
    EXTRACT_MAX_IMAGES: int = 6

    # --------------------------------------------------------------- generation
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-haiku-5-5"
    LLM_MAX_COST_PER_RUN_EUR: float = 2.0
    LLM_MAX_TOKENS: int = 8000

    # ------------------------------------------------------------------ preview
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_PAGES_PROJECT: str = "relaunch-previews"
    PREVIEW_EXPIRE_DAYS: int = 45
    SITE_DIR: Path = PROJECT_ROOT / "site"

    # ------------------------------------------------------------------- review
    AUTO_APPROVE: bool = False
    REVIEW_HOST: str = "127.0.0.1"
    REVIEW_PORT: int = 8787

    # ------------------------------------------------------------------ sending
    SENDER_BACKEND: Literal["dryrun", "instantly"] = "dryrun"
    INSTANTLY_API_KEY: str = ""
    INSTANTLY_CAMPAIGN_ID: str = ""
    DAILY_SEND_LIMIT_START: int = 30
    DAILY_SEND_LIMIT_MAX: int = 150
    DAILY_SEND_LIMIT_RAMP_PER_WEEK: int = 20
    SEND_WINDOW_START_HOUR: int = 8
    SEND_WINDOW_END_HOUR: int = 17
    SEND_WEEKDAYS_ONLY: bool = True
    OUTBOX_DIR: Path = PROJECT_ROOT / "outbox"
    FOLLOWUP_1_DAYS: int = 3
    FOLLOWUP_2_DAYS: int = 7

    # ------------------------------------------------------------------- report
    RESEND_API_KEY: str = ""
    REPORT_EMAIL_TO: str = ""  # e.g. auguyoga@gmail.com (receive only)
    REPORT_EMAIL_FROM: str = ""  # a verified sender on a *separate* domain, never the reply address

    # -------------------------------------------------------------------- costs
    COST_PLACES_PER_REQUEST_EUR: float = 0.030  # Text Search (Advanced) ≈ 32 USD / 1000
    COST_PAGESPEED_PER_REQUEST_EUR: float = 0.0
    COST_LLM_INPUT_PER_MTOK_EUR: float = 0.10
    COST_LLM_OUTPUT_PER_MTOK_EUR: float = 0.50

    @field_validator("DATA_DIR", "OUTBOX_DIR", "SITE_DIR", "REGION_CITIES_FILE", mode="before")
    @classmethod
    def _expand(cls, v):
        return Path(str(v)).expanduser()

    # ------------------------------------------------------------ derived values
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Supabase hands out postgres:// URLs; SQLAlchemy wants a driver name.
            if url.startswith("postgres://"):
                url = "postgresql+psycopg://" + url[len("postgres://"):]
            elif url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url[len("postgresql://"):]
            return url
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.DATA_DIR / 'pipeline.db'}"

    @property
    def preview_base_url(self) -> str:
        return (self.PREVIEW_BASE_URL or f"https://{self.PREVIEW_DOMAIN}").rstrip("/")

    @property
    def industry_dir(self) -> Path:
        return PROJECT_ROOT / "industries" / self.INDUSTRY

    @property
    def brand_name(self) -> str:
        return self.BRAND_NAME or self.SENDER_NAME

    def has(self, key: str) -> bool:
        """True if the given secret/config value is set (non-empty)."""
        return bool(getattr(self, key, ""))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
