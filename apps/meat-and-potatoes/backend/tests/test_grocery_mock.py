from app.services.grocery.mock import MockProvider


def test_mock_finds_close_match():
    prov = MockProvider()
    results = prov.search("boneless chicken breasts")
    assert results
    assert any("Chicken Breast" in p.name for p in results)
    assert all(p.item_id for p in results)
    assert all(p.in_stock for p in results)


def test_mock_ids_are_deterministic():
    a = MockProvider().search("ground beef")[0].item_id
    b = MockProvider().search("ground beef")[0].item_id
    assert a == b


def test_mock_never_empty():
    assert MockProvider().search("xyzzy nonsense") != []
