from app.services.grocery.scraperapi import item_id_from_url, parse_items

# Shape taken from a real ScraperAPI /structured/walmart/search response.
REAL_ISH = {
    "items": [
        {
            "availability": "In stock",
            "brand": "All",
            "id": "37WO59TLNCDG",
            "name": "All Natural* 80% Lean/20% Fat Ground Beef Chuck, 1 lb Tray",
            "price": 0,
            "rating": {"average_rating": 4.5, "number_of_reviews": 105588},
            "seller": "Walmart.com",
            "url": "https://www.walmart.com/ip/80-Lean-20-Fat-Ground-Beef-Chuck-1-lb-Tray/479601462?classType=REGULAR",
        },
        {
            "availability": "Out of stock",
            "id": "ZZ",
            "name": "Some Frozen Thing",
            "price": "$4.98",
            "url": "https://www.walmart.com/ip/887766",
        },
    ],
    "meta": {"page": 1, "pages": 3},
}


def test_item_id_comes_from_url_not_opaque_id():
    prods = parse_items(REAL_ISH, "ground beef")
    assert prods[0].item_id == "479601462"
    assert prods[1].item_id == "887766"


def test_zero_price_is_unknown_and_string_price_parses():
    prods = parse_items(REAL_ISH, "ground beef")
    assert prods[0].price is None
    assert prods[1].price == 4.98


def test_availability_maps_to_in_stock():
    prods = parse_items(REAL_ISH, "x")
    assert prods[0].in_stock is True
    assert prods[1].in_stock is False


def test_item_id_from_url_edge_cases():
    assert item_id_from_url(None) == ""
    assert item_id_from_url("https://www.walmart.com/browse/food") == ""
    assert item_id_from_url("https://www.walmart.com/ip/slug-here/12345678?a=b") == "12345678"
