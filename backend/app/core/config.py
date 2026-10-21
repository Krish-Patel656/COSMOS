"""Application settings.

Defaults are chosen so that ``uvicorn app.main:app`` works on a clean checkout
with no services running: SQLite on disk and an in-process cache. Setting
``DATABASE_URL`` to a Postgres DSN and ``REDIS_URL`` to a Redis instance
switches both subsystems with no code changes, which is how the deployed
configuration differs from the local one.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -----------------------------------------------------
    app_name: str = "COSMOS API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Persistence -----------------------------------------------------
    database_url: str = f"sqlite+aiosqlite:///{BACKEND_ROOT / 'cosmos.db'}"
    database_echo: bool = False

    # --- Cache -----------------------------------------------------------
    redis_url: str | None = None
    cache_ttl_seconds: int = 300
    cache_max_entries: int = 2048

    # --- Auth ------------------------------------------------------------
    secret_key: str = "dev-only-insecure-key-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # --- CORS ------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # --- Data ingestion --------------------------------------------------
    nasa_tap_url: str = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
    ingest_timeout_seconds: float = 180.0
    ingest_row_limit: int | None = None
    snapshot_path: Path = BACKEND_ROOT / "app" / "data" / "exoplanet_snapshot.json.gz"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string so the value is .env friendly."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
