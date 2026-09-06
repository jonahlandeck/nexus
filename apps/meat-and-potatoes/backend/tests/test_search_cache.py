from datetime import datetime, timedelta, timezone

import httpx
import respx

from app import store
from app.services.grocery.cache import CachedWalmartSearch, cache_key
from app.services.grocery.scraperapi import ENDPOINT, ScraperApiProvider

_PAYLOAD = {
    "items": [
        {
            "id": "37WO59TLNCDG",  # opaque token - NOT usable for add-to-cart
            "name": "Great Value Ground Beef",
            "price": 0,  # this feed usually omits prices
            "url": "https://www.walmart.com/ip/great-value-ground-beef/555123?classType=REGULAR",
            "image": "https://img/555.jpg",
            "availability": "In stock",
            "seller": "Walmart",
            "rating": {"average_rating": 4.4, "number_of_reviews": 90},
        }
    ],
    "meta": {"page": 1, "pages": 3},
}


def _provider(ttl_days=7):
    inner = ScraperApiProvider(api_key="test-key", tld="com")
    return CachedWalmartSearch(inner, tld="com", ttl_days=ttl_days)


@respx.mock
async def test_second_identical_search_is_a_cache_hit(d1):
    route = respx.get(ENDPOINT).mock(return_value=httpx.Response(200, json=_PAYLOAD))
    prov = _provider()

    first = await prov.search("ground beef", d1)
    second = await prov.search("Ground  Beef", d1)  # normalizes to same key

    # numeric US item id is pulled out of the product URL, not the opaque `id`
    assert first[0].item_id == "555123"
    assert second[0].item_id == "555123"
    assert first[0].price is None  # 0 in the feed -> unknown, not $0.00
    assert route.call_count == 1
    assert prov.hits == 1 and prov.misses == 1


@respx.mock
async def test_force_refresh_bypasses_cache(d1):
    route = respx.get(ENDPOINT).mock(return_value=httpx.Response(200, json=_PAYLOAD))
    prov = _provider()

    await prov.search("milk", d1)
    await prov.search("milk", d1, force=True)

    assert route.call_count == 2


@respx.mock
async def test_expired_row_is_refetched(d1):
    route = respx.get(ENDPOINT).mock(return_value=httpx.Response(200, json=_PAYLOAD))
    prov = _provider(ttl_days=1)
    await prov.search("eggs", d1)

    stale = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    await d1.run(
        "UPDATE search_cache SET fetched_at = ? WHERE cache_key = ?",
        stale,
        cache_key("eggs", "com", 1),
    )

    await prov.search("eggs", d1)
    assert route.call_count == 2
