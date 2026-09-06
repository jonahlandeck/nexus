"""Pick a GroceryProvider from settings. `scraperapi` gets wrapped in the cache."""
from __future__ import annotations

from ...config import Settings
from .base import GroceryProvider
from .cache import CachedWalmartSearch
from .links import LinksProvider
from .mock import MockProvider
from .scraperapi import ScraperApiProvider


def get_provider(cfg: Settings) -> GroceryProvider:
    choice = (cfg.map_provider or "mock").lower()

    if choice == "mock":
        return MockProvider()
    if choice == "links":
        return LinksProvider()
    if choice == "scraperapi":
        inner = ScraperApiProvider(api_key=cfg.scraperapi_key, tld=cfg.scraperapi_tld)
        return CachedWalmartSearch(
            inner,
            tld=cfg.scraperapi_tld,
            ttl_days=cfg.search_cache_ttl_days,
        )
    raise ValueError(f"Unknown MAP_PROVIDER={choice!r}. Use scraperapi | mock | links.")
