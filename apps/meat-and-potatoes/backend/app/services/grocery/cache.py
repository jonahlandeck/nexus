"""Persistent search cache so the same Walmart query never spends two credits.

Wraps any GroceryProvider. A cache row (in D1 table ``search_cache``) stores the
raw parsed products as JSON, keyed by a hash of (normalized query, tld, page).
Rows older than the TTL are refetched.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from ... import store
from .base import GroceryProvider, Product

log = logging.getLogger("meatpotatoes.searchcache")


def cache_key(query: str, tld: str, page: int | None) -> str:
    norm = re.sub(r"\s+", " ", query.strip().lower())
    return hashlib.sha1(f"{norm}|{tld}|{page or 1}".encode()).hexdigest()


class CachedWalmartSearch(GroceryProvider):
    """Read-through cache around a real provider."""

    def __init__(
        self,
        inner: GroceryProvider,
        tld: str = "com",
        ttl_days: int = 7,
    ) -> None:
        self._inner = inner
        self._tld = tld
        self._ttl = timedelta(days=max(0, ttl_days))
        self.name = f"{inner.name}+cache"
        self.uses_credits = inner.uses_credits
        # in-process counters for the stats endpoint (per request on Workers)
        self.hits = 0
        self.misses = 0

    async def search(
        self, query: str, db: object | None = None, *, force: bool = False
    ) -> list[Product]:
        key = cache_key(query, self._tld, 1)
        row = await store.cache_get(db, key)
        fresh = (
            row is not None
            and self._ttl.total_seconds() > 0
            and _aware(row["fetched_at"]) > datetime.now(timezone.utc) - self._ttl
        )
        if row is not None and fresh and not force:
            self.hits += 1
            log.info('cache=hit query="%s"', query)
            return _from_cache(row["response_json"], query)

        self.misses += 1
        log.info('cache=miss query="%s" (force=%s)', query, force)
        products = await self._inner.search(query, db, force=force)
        payload = json.dumps([asdict(p) for p in products])
        await store.cache_put(db, key, query, payload)
        return products

    async def stats(self, db: object | None = None) -> dict:
        base = await store.cache_stats(db)
        base["hits"] = self.hits
        base["misses"] = self.misses
        return base

    def search_url(self, query: str) -> str:
        return self._inner.search_url(query)

    def build_cart_link(self, items):
        return self._inner.build_cart_link(items)


def _aware(value) -> datetime:
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _from_cache(blob: str, query: str) -> list[Product]:
    rows = json.loads(blob)
    out: list[Product] = []
    for d in rows:
        d = dict(d)
        d["query"] = query
        out.append(Product(**d))
    return out
