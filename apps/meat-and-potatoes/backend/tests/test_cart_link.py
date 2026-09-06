from urllib.parse import parse_qs, urlparse

from app.services.grocery.base import build_cart_link, build_cart_steps, search_url


def test_cart_link_format():
    url = build_cart_link([("111", 2), ("222", 1)])
    parsed = urlparse(url)
    assert parsed.netloc == "affil.walmart.com"
    assert parsed.path == "/cart/addToCart"
    items = parse_qs(parsed.query)["items"][0]
    assert items == "111|2,222|1"


def test_cart_link_skips_blank_ids_and_floors_qty():
    url = build_cart_link([("", 3), ("999", 0)])
    items = parse_qs(urlparse(url).query)["items"][0]
    assert items == "999|1"


def test_cart_link_empty():
    assert build_cart_link([]) == "https://affil.walmart.com/cart/addToCart"


def test_cart_steps_one_per_link_by_default():
    steps = build_cart_steps([("111", 2), ("222", 1), ("333", 4)])
    assert len(steps) == 3
    first = parse_qs(urlparse(steps[0]).query)["items"][0]
    assert first == "111|2"


def test_cart_steps_chunks_and_skips_blank_ids():
    steps = build_cart_steps([("111", 1), ("", 9), ("222", 1), ("333", 1)], chunk_size=2)
    assert len(steps) == 2
    assert parse_qs(urlparse(steps[0]).query)["items"][0] == "111|1,222|1"
    assert parse_qs(urlparse(steps[1]).query)["items"][0] == "333|1"


def test_cart_steps_empty():
    assert build_cart_steps([]) == []


def test_search_url():
    assert search_url("ground beef") == "https://www.walmart.com/search?q=ground+beef"
    assert "walmart.ca" in search_url("milk", tld="ca")
