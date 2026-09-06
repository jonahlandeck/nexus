"""GroceryProvider interface + shared helpers (cart deep link, search URL)."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from urllib.parse import quote_plus

ADD_TO_CART_BASE = "https://affil.walmart.com/cart/addToCart"
WALMART_SEARCH_BASE = "https://www.walmart.com/search"


class GroceryProviderError(RuntimeError):
    """Raised when an upstream grocery lookup fails."""


@dataclass
class Product:
    query: str
    item_id: str
    name: str
    price: float | None = None
    in_stock: bool = True
    image_url: str | None = None
    product_url: str | None = None
    seller: str | None = None
    rating: dict = field(default_factory=dict)


def build_cart_link(items: list[tuple[str, int]]) -> str:
    """items -> https://affil.walmart.com/cart/addToCart?items=ID|QTY,ID|QTY

    Only rows with a truthy item_id are included.
    """
    parts = [f"{iid}|{max(1, int(qty))}" for iid, qty in items if iid]
    if not parts:
        return ADD_TO_CART_BASE
    return f"{ADD_TO_CART_BASE}?items={quote_plus(','.join(parts))}"


def build_cart_steps(
    items: list[tuple[str, int]], chunk_size: int = 1
) -> list[str]:
    """Split items into groups of at most ``chunk_size`` and return one
    addToCart URL per group.

    Walmart's addToCart deep link silently drops items once the batch (or the
    URL) gets large, so a big all-in-one link is unreliable. Opening several
    small links in sequence is not.
    """
    picked = [(iid, qty) for iid, qty in items if iid]
    size = max(1, int(chunk_size))
    return [
        build_cart_link(picked[i : i + size]) for i in range(0, len(picked), size)
    ]


def search_url(query: str, tld: str = "com") -> str:
    domain = "walmart.ca" if tld == "ca" else "walmart.com"
    return f"https://www.{domain}/search?q={quote_plus(query)}"


class GroceryProvider(abc.ABC):
    name: str = "base"
    uses_credits: bool = False

    @abc.abstractmethod
    def search(self, query: str, *, force: bool = False) -> list[Product]:
        ...

    def search_url(self, query: str) -> str:
        return search_url(query)

    def build_cart_link(self, items: list[tuple[str, int]]) -> str:
        return build_cart_link(items)
