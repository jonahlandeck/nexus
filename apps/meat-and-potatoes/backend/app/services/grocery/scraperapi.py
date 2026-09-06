"""ScraperAPI structured Walmart Search provider.

GET https://api.scraperapi.com/structured/walmart/search
  ?api_key=...&query=...&tld=com&output_format=json

Response: { items: [ {id, name, price, url, image, availability, seller,
                     rating: {average_rating, number_of_reviews}} ],
            meta: {page, pages} }
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import GroceryProvider, GroceryProviderError, Product

ENDPOINT = "https://api.scraperapi.com/structured/walmart/search"
_OUT_OF_STOCK_HINTS = ("out of stock", "unavailable", "not available", "sold out")
# Walmart product URLs look like  /ip/<slug>/<numeric-us-item-id>?...  (slug optional)
_ITEM_ID_RE = re.compile(r"/ip/(?:[^/?#]+/)?(\d{4,})")


def item_id_from_url(url: str | None) -> str:
    if not url:
        return ""
    m = _ITEM_ID_RE.search(url)
    return m.group(1) if m else ""


def parse_items(payload: dict[str, Any], query: str) -> list[Product]:
    products: list[Product] = []
    for raw in payload.get("items", []) or []:
        avail = str(raw.get("availability", "") or "")
        in_stock = not any(h in avail.lower() for h in _OUT_OF_STOCK_HINTS)
        url = raw.get("url")
        # The numeric US item id (needed for the add-to-cart deep link) lives in the URL.
        # ScraperAPI's own `id` is an opaque token that the cart endpoint does not accept.
        numeric_id = item_id_from_url(url) or str(raw.get("id", "") or "")
        products.append(
            Product(
                query=query,
                item_id=numeric_id,
                name=str(raw.get("name", "") or ""),
                price=_as_float(raw.get("price")),
                in_stock=in_stock,
                image_url=raw.get("image"),
                product_url=url,
                seller=raw.get("seller"),
                rating=raw.get("rating") or {},
            )
        )
    return products


def _as_float(v: Any) -> float | None:
    """Parse a price. This search feed frequently omits prices (returns 0) - treat
    0 / blank as 'unknown' rather than a real $0.00."""
    if v in (None, "", 0, 0.0):
        return None
    try:
        f = float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None
    return f if f > 0 else None


class ScraperApiProvider(GroceryProvider):
    name = "scraperapi"
    uses_credits = True

    def __init__(self, api_key: str, tld: str = "com", timeout: float = 60.0) -> None:
        if not api_key:
            raise GroceryProviderError(
                "MAP_PROVIDER=scraperapi but SCRAPERAPI_KEY is empty. "
                "Add your key to apps/meat-and-potatoes/.env"
            )
        self._api_key = api_key
        self._tld = tld
        self._timeout = timeout

    async def search(
        self, query: str, db: object | None = None, *, force: bool = False
    ) -> list[Product]:
        params = {
            "api_key": self._api_key,
            "query": query,
            "tld": self._tld,
            "output_format": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as c:
                r = await c.get(ENDPOINT, params=params)
        except httpx.HTTPError as exc:
            raise GroceryProviderError(f"ScraperAPI request failed: {exc}") from exc
        if r.status_code == 401:
            raise GroceryProviderError("ScraperAPI rejected the key (401). Check SCRAPERAPI_KEY.")
        if r.status_code != 200:
            raise GroceryProviderError(
                f"ScraperAPI returned {r.status_code}: {r.text[:300]}"
            )
        try:
            payload = r.json()
        except ValueError as exc:
            raise GroceryProviderError("ScraperAPI returned non-JSON body") from exc
        return parse_items(payload, query)
