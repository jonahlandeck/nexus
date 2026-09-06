"""Weekly meal-plan generation + grocery-list consolidation.

`generate_plan_json` talks to the LLM; everything else is pure and unit-tested.
"""
from __future__ import annotations

import inspect
import re
from typing import Any, Callable

from . import llm
from ..config import Settings
from ..schemas import MEAL_PLAN_JSON_SCHEMA

_DESCRIPTORS = {
    "fresh", "large", "small", "medium", "ripe", "boneless", "skinless", "raw",
    "cooked", "dried", "ground", "chopped", "diced", "sliced", "minced", "whole",
    "organic", "low-sodium", "reduced-fat", "extra", "virgin", "unsalted", "salted",
    "of", "a", "an", "the",
}

_UNIT_ALIASES = {
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml",
    "liter": "l", "liters": "l", "l": "l",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp",
    "cup": "cup", "cups": "cup",
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "package": "pkg", "packages": "pkg", "pkg": "pkg",
    "bunch": "bunch", "bunches": "bunch",
    "piece": "piece", "pieces": "piece",
    "": "", "each": "", "unit": "", "units": "",
}


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\(.*?\)", "", name)          # drop parentheticals
    name = re.sub(r"[^a-z0-9\s-]", " ", name)    # punctuation -> space
    tokens = [t for t in name.split() if t and t not in _DESCRIPTORS]
    tokens = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens]  # naive singularize
    return " ".join(tokens).strip() or name.strip()


def normalize_unit(unit: str) -> str:
    return _UNIT_ALIASES.get((unit or "").lower().strip(), (unit or "").lower().strip())


def line_key(name: str, unit: str) -> str:
    return f"{normalize_name(name)}|{normalize_unit(unit)}"


def consolidate(
    plan: dict[str, Any], pantry: list[str] | None = None
) -> list[dict[str, Any]]:
    """Flatten every meal's ingredients into one shopping list.

    Sums quantities that share a normalized (name, unit); different units stay on
    separate lines. Anything whose normalized name matches a pantry entry is dropped.
    """
    pantry_norm = {normalize_name(p) for p in (pantry or [])}
    buckets: dict[str, dict[str, Any]] = {}

    for day in plan.get("days", []):
        for meal in day.get("meals", []):
            for ing in meal.get("ingredients", []):
                raw_name = str(ing.get("name", "")).strip()
                if not raw_name:
                    continue
                norm = normalize_name(raw_name)
                if norm in pantry_norm:
                    continue
                unit = normalize_unit(str(ing.get("unit", "")))
                key = f"{norm}|{unit}"
                try:
                    qty = float(ing.get("quantity", 0) or 0)
                except (TypeError, ValueError):
                    qty = 0.0
                if key not in buckets:
                    buckets[key] = {
                        "line_key": key,
                        "name": raw_name,
                        "quantity": 0.0,
                        "unit": unit,
                        "category": str(ing.get("category", "") or ""),
                    }
                buckets[key]["quantity"] += qty
                if not buckets[key]["category"] and ing.get("category"):
                    buckets[key]["category"] = str(ing["category"])

    return sorted(buckets.values(), key=lambda x: (x["category"], x["name"].lower()))


def _profile_lines(profile: dict[str, Any]) -> str:
    if not profile:
        return "(no profile captured - use sensible balanced defaults)"
    return "\n".join(f"- {k}: {v}" for k, v in profile.items())


def build_messages(
    profile: dict[str, Any],
    prompt: str,
    days: int,
    meals_per_day: list[str],
) -> list[dict[str, str]]:
    system = (
        "You are a meal planner. Produce a realistic, varied weekly plan that respects the "
        "user's diet, allergies, budget, cooking time and equipment. Use common grocery-store "
        "ingredients. Give every ingredient a quantity and a unit (use 'each' when countable). "
        "Mark pantry staples (salt, pepper, oil, common spices) with staple=true. "
        "Return ONLY JSON matching the provided schema."
    )
    user = (
        f"Plan {days} days. Meal slots each day: {', '.join(meals_per_day)}.\n\n"
        f"User profile:\n{_profile_lines(profile)}\n\n"
        f"Extra request for this week: {prompt or '(none)'}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def generate_plan_json(
    profile: dict[str, Any],
    prompt: str,
    days: int = 7,
    meals_per_day: list[str] | None = None,
    cfg: Settings | None = None,
    _llm: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    meals_per_day = meals_per_day or ["breakfast", "lunch", "dinner"]
    messages = build_messages(profile, prompt, days, meals_per_day)
    if _llm is not None:
        plan = _llm(messages)
        if inspect.isawaitable(plan):
            plan = await plan
    else:
        plan = await llm.generate_json(messages, cfg, schema=MEAL_PLAN_JSON_SCHEMA)
    if "days" not in plan or not isinstance(plan["days"], list):
        raise llm.LLMError("Meal plan JSON missing 'days' array.")
    return plan
