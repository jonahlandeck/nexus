"""Offline canned Walmart data - lets the whole app run with no network / no key."""
from __future__ import annotations

import difflib
import hashlib

from .base import GroceryProvider, Product

# name -> (product name, price, size text)
_CATALOG: dict[str, tuple[str, float, str]] = {
    "chicken breast": ("Fresh Boneless Skinless Chicken Breast", 9.32, "2.5 lb"),
    "ground beef": ("All Natural 80/20 Ground Beef", 6.97, "1 lb"),
    "ground turkey": ("Honeysuckle White 93/7 Ground Turkey", 5.48, "1 lb"),
    "salmon": ("Fresh Atlantic Salmon Fillet", 11.64, "1 lb"),
    "egg": ("Great Value Large White Eggs", 3.12, "12 ct"),
    "milk": ("Great Value 2% Reduced Fat Milk", 3.28, "1 gal"),
    "greek yogurt": ("Great Value Plain Greek Nonfat Yogurt", 4.62, "32 oz"),
    "cheddar cheese": ("Great Value Mild Cheddar Shredded Cheese", 2.34, "8 oz"),
    "butter": ("Great Value Salted Sweet Cream Butter", 3.97, "16 oz"),
    "olive oil": ("Great Value Extra Virgin Olive Oil", 6.84, "17 fl oz"),
    "rice": ("Great Value Long Grain Enriched White Rice", 2.86, "32 oz"),
    "brown rice": ("Great Value Whole Grain Brown Rice", 3.12, "32 oz"),
    "pasta": ("Great Value Spaghetti", 1.24, "16 oz"),
    "bread": ("Great Value White Sandwich Bread", 1.42, "20 oz"),
    "tortilla": ("Great Value Flour Tortillas", 2.18, "10 ct"),
    "black beans": ("Great Value Black Beans", 0.92, "15 oz can"),
    "chickpeas": ("Great Value Garbanzo Beans", 0.92, "15 oz can"),
    "canned tomatoes": ("Great Value Diced Tomatoes", 0.98, "14.5 oz can"),
    "tomato": ("Fresh Roma Tomatoes", 0.88, "1 lb"),
    "onion": ("Fresh Yellow Onion", 0.74, "1 lb"),
    "garlic": ("Fresh Garlic", 0.58, "3 ct"),
    "bell pepper": ("Fresh Green Bell Pepper", 0.68, "each"),
    "broccoli": ("Fresh Broccoli Crown", 1.98, "1 lb"),
    "spinach": ("Fresh Baby Spinach", 2.68, "10 oz"),
    "carrot": ("Fresh Whole Carrots", 1.18, "2 lb"),
    "potato": ("Fresh Russet Potatoes", 4.27, "5 lb"),
    "sweet potato": ("Fresh Sweet Potatoes", 1.34, "1 lb"),
    "banana": ("Fresh Bananas", 0.52, "1 lb"),
    "apple": ("Fresh Gala Apples", 1.64, "1 lb"),
    "avocado": ("Fresh Hass Avocado", 0.98, "each"),
    "lemon": ("Fresh Lemon", 0.62, "each"),
    "oats": ("Great Value Old Fashioned Oats", 3.34, "42 oz"),
    "peanut butter": ("Great Value Creamy Peanut Butter", 2.64, "16 oz"),
    "almond": ("Great Value Whole Almonds", 5.98, "16 oz"),
    "frozen mixed vegetables": ("Great Value Mixed Vegetables", 1.12, "12 oz"),
    "salt": ("Great Value Iodized Salt", 0.52, "26 oz"),
    "black pepper": ("Great Value Ground Black Pepper", 1.86, "3 oz"),
}


def _fake_id(name: str) -> str:
    return str(int(hashlib.sha1(name.encode()).hexdigest()[:10], 16))


class MockProvider(GroceryProvider):
    name = "mock"
    uses_credits = False

    def search(self, query: str, *, force: bool = False) -> list[Product]:
        from ..planner import normalize_name

        norm = normalize_name(query)
        keys = list(_CATALOG)
        best = difflib.get_close_matches(norm, keys, n=3, cutoff=0.3)
        if not best:
            best = [k for k in keys if norm and (norm in k or k in norm)][:3]
        out: list[Product] = []
        for k in best or keys[:1]:
            pname, price, size = _CATALOG[k]
            out.append(
                Product(
                    query=query,
                    item_id=_fake_id(k),
                    name=f"{pname} ({size})",
                    price=price,
                    in_stock=True,
                    image_url=None,
                    product_url=f"https://www.walmart.com/ip/{_fake_id(k)}",
                    seller="Walmart",
                    rating={"average_rating": 4.5, "number_of_reviews": 128},
                )
            )
        return out
