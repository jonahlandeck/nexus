"""Application configuration, loaded from apps/meat-and-potatoes/.env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/meat-and-potatoes/  (two levels up from this file's backend/app/)
APP_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=APP_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout: float = 180.0

    map_provider: str = "mock"  # scraperapi | mock | links
    scraperapi_key: str = ""
    scraperapi_tld: str = "com"

    search_cache_ttl_days: int = 7

    db_path: str = "backend/data/map.db"
    cors_origin: str = "http://localhost:5173"

    @property
    def db_url(self) -> str:
        p = Path(self.db_path)
        if not p.is_absolute():
            p = APP_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{p}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
