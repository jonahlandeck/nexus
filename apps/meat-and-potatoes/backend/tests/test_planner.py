from app.services import planner

FAKE_PLAN = {
    "days": [
        {
            "day": "Monday",
            "meals": [
                {
                    "slot": "dinner",
                    "title": "Chicken & rice",
                    "ingredients": [
                        {"name": "Chicken Breast", "quantity": 1, "unit": "lb", "category": "meat"},
                        {"name": "white rice", "quantity": 2, "unit": "cups", "category": "grains"},
                        {"name": "Salt", "quantity": 1, "unit": "tsp", "staple": True},
                    ],
                }
            ],
        },
        {
            "day": "Tuesday",
            "meals": [
                {
                    "slot": "dinner",
                    "title": "Chicken tacos",
                    "ingredients": [
                        {"name": "chicken breasts", "quantity": 1.5, "unit": "lbs", "category": "meat"},
                        {"name": "onion", "quantity": 1, "unit": "each", "category": "produce"},
                    ],
                }
            ],
        },
    ],
    "notes": "",
}


def test_consolidate_sums_matching_name_and_unit():
    lines = planner.consolidate(FAKE_PLAN)
    by_key = {l["line_key"]: l for l in lines}
    # "Chicken Breast" (lb) + "chicken breasts" (lbs) collapse to one line
    chicken = by_key["chicken breast|lb"]
    assert chicken["quantity"] == 2.5
    assert by_key["white rice|cup"]["quantity"] == 2
    assert "onion|" in by_key


def test_consolidate_drops_pantry_items():
    lines = planner.consolidate(FAKE_PLAN, pantry=["onions", "rice"])
    keys = {l["line_key"] for l in lines}
    assert not any(k.startswith("onion|") for k in keys)
    assert not any(k.startswith("rice|") for k in keys)
    assert any(k.startswith("chicken breast|") for k in keys)


def test_generate_plan_json_uses_injected_llm():
    calls = []

    def fake_llm(messages):
        calls.append(messages)
        return FAKE_PLAN

    out = planner.generate_plan_json({"dietary_pattern": "omnivore"}, "high protein", _llm=fake_llm)
    assert out is FAKE_PLAN
    assert calls and calls[0][0]["role"] == "system"


def test_normalize_unit_aliases():
    assert planner.normalize_unit("Tablespoons") == "tbsp"
    assert planner.normalize_unit("lbs") == "lb"
    assert planner.normalize_unit("each") == ""
