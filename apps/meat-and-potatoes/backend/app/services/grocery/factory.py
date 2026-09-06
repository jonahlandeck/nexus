"""Pick a GroceryProvider from settings. `scraperapi` gets wrapped in the cache."""
from __future__ import annotations

from functools import lru_cache

from ...config import get_settings
from ...db import SessionLocal
from .base import GroceryProvider
from .cache import CachedWalmartSearch
from .links import LinksProvider
from .mock import MockProvider
from .scraperapi import ScraperApiProvider


@lru_cache
def get_provider() -> GroceryProvider:
    s = get_settings()
    choice = (s.map_provider or "mock").lower()

    if choice == "mock":
        return MockProvider()
    if choice == "links":
        return LinksProvider()
    if choice == "scraperapi":
        inner = ScraperApiProvider(api_key=s.scraperapi_key, tld=s.scraperapi_tld)
        return CachedWalmartSearch(
            inner,
            session_factory=SessionLocal,
            tld=s.scraperapi_tld,
            ttl_days=s.search_cache_ttl_days,
        )
    raise ValueError(f"Unknown MAP_PROVIDER={choice!r}. Use scraperapi | mock | links.")
