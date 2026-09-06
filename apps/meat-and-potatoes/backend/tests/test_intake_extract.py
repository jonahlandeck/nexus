from app.services.intake_agent import deep_merge


def test_deep_merge_nested_dicts():
    base = {"macros": {"protein_g": 150}, "allergies": ["peanuts"]}
    patch = {"macros": {"carbs_g": 200}, "dietary_pattern": "omnivore"}
    out = deep_merge(base, patch)
    assert out["macros"] == {"protein_g": 150, "carbs_g": 200}
    assert out["dietary_pattern"] == "omnivore"
    assert out["allergies"] == ["peanuts"]


def test_deep_merge_replaces_lists():
    out = deep_merge({"allergies": ["peanuts"]}, {"allergies": ["shellfish", "gluten"]})
    assert out["allergies"] == ["shellfish", "gluten"]


def test_deep_merge_empty_patch_is_noop():
    base = {"a": 1}
    assert deep_merge(base, {}) == base
