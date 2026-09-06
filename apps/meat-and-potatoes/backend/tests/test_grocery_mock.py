from app.services.grocery.mock import MockProvider


async def test_mock_finds_close_match():
    prov = MockProvider()
    results = await prov.search("boneless chicken breasts")
    assert results
    assert any("Chicken Breast" in p.name for p in results)
    assert all(p.item_id for p in results)
    assert all(p.in_stock for p in results)


async def test_mock_ids_are_deterministic():
    a = (await MockProvider().search("ground beef"))[0].item_id
    b = (await MockProvider().search("ground beef"))[0].item_id
    assert a == b


async def test_mock_never_empty():
    assert await MockProvider().search("xyzzy nonsense") != []
