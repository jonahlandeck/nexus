"""Persistent search cache so the same Walmart query never spends two credits.

Wraps any GroceryProvider. A cache row stores the raw upstream JSON keyed by a
hash of (normalized query, tld, page). Rows older than the TTL are refetched.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import SearchCache
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
        session_factory,
        tld: str = "com",
        ttl_days: int = 7,
    ) -> None:
        self._inner = inner
        self._session_factory = session_factory
        self._tld = tld
        self._ttl = timedelta(days=max(0, ttl_days))
        self.name = f"{inner.name}+cache"
        self.uses_credits = inner.uses_credits
        # in-process counters for the stats endpoint
        self.hits = 0
        self.misses = 0

    def search(self, query: str, *, force: bool = False) -> list[Product]:
        key = cache_key(query, self._tld, 1)
        with self._session_factory() as db:  # type: Session
            row = db.get(SearchCache, key)
            fresh = (
                row is not None
                and self._ttl.total_seconds() > 0
                and _aware(row.fetched_at) > datetime.now(timezone.utc) - self._ttl
            )
            if row is not None and fresh and not force:
                self.hits += 1
                log.info('cache=hit query="%s"', query)
                return _from_cache(row.response_json, query)

            self.misses += 1
            log.info('cache=miss query="%s" (force=%s)', query, force)
            products = self._inner.search(query, force=force)
            payload = json.dumps([asdict(p) for p in products])
            if row is None:
                db.add(SearchCache(cache_key=key, query=query, response_json=payload))
            else:
                row.response_json = payload
                row.query = query
                row.fetched_at = datetime.now(timezone.utc)
            db.commit()
            return products

    # -- stats helpers -------------------------------------------------------

    def stats(self) -> dict:
        with self._session_factory() as db:  # type: Session
            entries = db.scalar(select(func.count()).select_from(SearchCache)) or 0
            last = db.scalar(select(func.max(SearchCache.fetched_at)))
        return {
            "entries": int(entries),
            "hits": self.hits,
            "misses": self.misses,
            "last_fetch_at": last.isoformat() if last else None,
        }

    def search_url(self, query: str) -> str:
        return self._inner.search_url(query)

    def build_cart_link(self, items):
        return self._inner.build_cart_link(items)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _from_cache(blob: str, query: str) -> list[Product]:
    rows = json.loads(blob)
    out: list[Product] = []
    for d in rows:
        d = dict(d)
        d["query"] = query
        out.append(Product(**d))
    return out
