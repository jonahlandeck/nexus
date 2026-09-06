"""Application configuration.

On Cloudflare Workers there is no ``.env`` file and no ``os.environ`` for
``[vars]`` / secrets - they arrive on the per-request ``env`` binding object.
``get_settings(env)`` builds a :class:`Settings` from that object (falling back
to ``os.environ`` so the code still runs under pytest / a plain uvicorn).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _get(env: Any, key: str, default: str = "") -> str:
    if env is not None:
        val = getattr(env, key, None)
        if val is None and hasattr(env, "get"):
            try:
                val = env.get(key)
            except Exception:
                val = None
        if val is not None:
            return str(val)
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout: float = 180.0

    map_provider: str = "mock"  # scraperapi | mock | links
    scraperapi_key: str = ""
    scraperapi_tld: str = "com"

    search_cache_ttl_days: int = 7

    # Origin allowed through CORS (the deployed SPA is same-origin, so this is
    # only relevant for local dev against the Vite server).
    cors_origin: str = "http://localhost:5173"


def get_settings(env: Any = None) -> Settings:
    def num(key: str, default: float) -> float:
        try:
            return float(_get(env, key, str(default)))
        except (TypeError, ValueError):
            return default

    return Settings(
        ollama_url=_get(env, "OLLAMA_URL", "http://localhost:11434"),
        ollama_model=_get(env, "OLLAMA_MODEL", "qwen2.5:7b-instruct"),
        ollama_timeout=num("OLLAMA_TIMEOUT", 180.0),
        map_provider=_get(env, "MAP_PROVIDER", "mock").lower() or "mock",
        scraperapi_key=_get(env, "SCRAPERAPI_KEY", ""),
        scraperapi_tld=_get(env, "SCRAPERAPI_TLD", "com"),
        search_cache_ttl_days=int(num("SEARCH_CACHE_TTL_DAYS", 7)),
        cors_origin=_get(env, "CORS_ORIGIN", "http://localhost:5173"),
    )
