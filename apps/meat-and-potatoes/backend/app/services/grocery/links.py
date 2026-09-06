"""Zero-credit provider: no search calls at all.

Every grocery line just gets a walmart.com/search link; the cart still uses the
add-to-cart deep link (built from item ids the user pastes in manually, if any).
"""
from __future__ import annotations

from .base import GroceryProvider, Product


class LinksProvider(GroceryProvider):
    name = "links"
    uses_credits = False

    def search(self, query: str, *, force: bool = False) -> list[Product]:
        return []
