"""Data access for Meat And Potatoes, backed by Cloudflare D1.

Every function takes a :class:`app.d1.D1` handle and returns plain ``dict`` /
``list`` values shaped for the Pydantic response models. This module replaces
the old SQLAlchemy ORM (``db.py`` + ``models.py``); the table layout lives in
``migrations/0001_init.sql``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .d1 import D1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(blob: Any, default: Any) -> Any:
    if blob in (None, ""):
        return default
    if isinstance(blob, (dict, list)):
        return blob
    try:
        return json.loads(blob)
    except (TypeError, ValueError):
        return default


# --- profile ---------------------------------------------------------------


async def get_profile(db: D1) -> dict[str, Any]:
    row = await db.first("SELECT data FROM profiles WHERE id = 1")
    if row is None:
        await db.run(
            "INSERT INTO profiles (id, data, updated_at) VALUES (1, '{}', ?)", _now()
        )
        return {}
    return _loads(row["data"], {})


async def set_profile(db: D1, data: dict[str, Any]) -> dict[str, Any]:
    data = data or {}
    await db.run(
        "INSERT INTO profiles (id, data, updated_at) VALUES (1, ?1, ?2) "
        "ON CONFLICT(id) DO UPDATE SET data = ?1, updated_at = ?2",
        json.dumps(data),
        _now(),
    )
    return data


# --- intake --------------------------------------------------------------


async def get_intake(db: D1, session_id: str) -> dict[str, Any] | None:
    row = await db.first(
        "SELECT id, transcript, complete FROM intake_sessions WHERE id = ?",
        session_id,
    )
    if row is None:
        return None
    return {
        "session_id": row["id"],
        "transcript": _loads(row["transcript"], []),
        "complete": bool(row["complete"]),
    }


async def save_intake(
    db: D1, session_id: str, transcript: list[dict[str, str]], complete: bool
) -> None:
    now = _now()
    await db.run(
        "INSERT INTO intake_sessions (id, transcript, complete, created_at, updated_at) "
        "VALUES (?1, ?2, ?3, ?4, ?4) "
        "ON CONFLICT(id) DO UPDATE SET transcript = ?2, complete = ?3, updated_at = ?4",
        session_id,
        json.dumps(transcript),
        1 if complete else 0,
        now,
    )


# --- plans -------------------------------------------------------------------


async def create_plan(
    db: D1,
    *,
    prompt: str,
    profile_snapshot: dict[str, Any],
    notes: str,
    days: int,
    meals: list[dict[str, Any]],
) -> int:
    plan_id = await db.insert(
        "INSERT INTO plans (prompt, profile_snapshot, notes, days, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        prompt,
        json.dumps(profile_snapshot or {}),
        notes,
        days,
        _now(),
    )
    for meal in meals:
        meal_id = await db.insert(
            "INSERT INTO meals (plan_id, day, day_index, slot, title, description, "
            "servings, approx_calories) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            plan_id,
            meal["day"],
            meal["day_index"],
            meal["slot"],
            meal["title"],
            meal.get("description", ""),
            meal.get("servings", 1),
            meal.get("approx_calories"),
        )
        for ing in meal.get("ingredients", []):
            await db.run(
                "INSERT INTO ingredients (meal_id, name, quantity, unit, category, staple) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                meal_id,
                ing.get("name", ""),
                float(ing.get("quantity", 0) or 0),
                ing.get("unit", ""),
                ing.get("category", ""),
                1 if ing.get("staple") else 0,
            )
    return plan_id


async def get_plan_full(db: D1, plan_id: int) -> dict[str, Any] | None:
    plan = await db.first(
        "SELECT id, prompt, notes, days, created_at FROM plans WHERE id = ?", plan_id
    )
    if plan is None:
        return None
    meals = await db.all(
        "SELECT id, day, day_index, slot, title, description, servings, approx_calories "
        "FROM meals WHERE plan_id = ? ORDER BY id",
        plan_id,
    )
    ingredients = await db.all(
        "SELECT i.id, i.meal_id, i.name, i.quantity, i.unit, i.category, i.staple "
        "FROM ingredients i JOIN meals m ON m.id = i.meal_id "
        "WHERE m.plan_id = ? ORDER BY i.id",
        plan_id,
    )
    by_meal: dict[int, list[dict[str, Any]]] = {}
    for ing in ingredients:
        by_meal.setdefault(ing["meal_id"], []).append(
            {
                "id": ing["id"],
                "name": ing["name"],
                "quantity": ing["quantity"],
                "unit": ing["unit"],
                "category": ing["category"],
                "staple": bool(ing["staple"]),
            }
        )
    for meal in meals:
        meal["ingredients"] = by_meal.get(meal["id"], [])
    plan["meals"] = meals
    return plan


async def latest_plan_id(db: D1) -> int | None:
    return await db.value("SELECT id FROM plans ORDER BY id DESC LIMIT 1")


def plan_to_days(plan: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the {days:[{day, meals:[{...ingredients}]}]} shape for consolidation."""
    days: dict[str, dict[str, Any]] = {}
    for m in plan["meals"]:
        day = days.setdefault(m["day"], {"day": m["day"], "meals": []})
        day["meals"].append(
            {
                "slot": m["slot"],
                "title": m["title"],
                "ingredients": [
                    {
                        "name": i["name"],
                        "quantity": i["quantity"],
                        "unit": i["unit"],
                        "category": i["category"],
                        "staple": i["staple"],
                    }
                    for i in m["ingredients"]
                ],
            }
        )
    return {"days": list(days.values()), "notes": plan["notes"]}


# --- pantry --------------------------------------------------------------


async def list_pantry(db: D1) -> list[dict[str, Any]]:
    return await db.all("SELECT id, name FROM pantry_items ORDER BY name")


async def add_pantry(db: D1, name: str) -> dict[str, Any]:
    existing = await db.first("SELECT id, name FROM pantry_items WHERE name = ?", name)
    if existing:
        return existing
    new_id = await db.insert(
        "INSERT INTO pantry_items (name, created_at) VALUES (?, ?)", name, _now()
    )
    return {"id": new_id, "name": name}


async def delete_pantry(db: D1, item_id: int) -> None:
    await db.run("DELETE FROM pantry_items WHERE id = ?", item_id)


# --- product matches --------------------------------------------------------

_MATCH_COLS = (
    "id, plan_id, line_key, query, display_name, quantity_needed, item_id, "
    "product_name, price, in_stock, image_url, product_url, seller, "
    "cart_quantity, manual"
)


def _match_row(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    row["in_stock"] = bool(row["in_stock"])
    row["manual"] = bool(row["manual"])
    return row


async def matches_for_plan(db: D1, plan_id: int) -> list[dict[str, Any]]:
    rows = await db.all(
        f"SELECT {_MATCH_COLS} FROM product_matches WHERE plan_id = ?", plan_id
    )
    return [_match_row(r) for r in rows]


async def get_match(db: D1, match_id: int) -> dict[str, Any] | None:
    row = await db.first(
        f"SELECT {_MATCH_COLS} FROM product_matches WHERE id = ?", match_id
    )
    return _match_row(row) if row else None


async def create_match(
    db: D1,
    *,
    plan_id: int,
    line_key: str,
    query: str,
    display_name: str,
    quantity_needed: float,
    cart_quantity: int,
) -> int:
    return await db.insert(
        "INSERT INTO product_matches (plan_id, line_key, query, display_name, "
        "quantity_needed, cart_quantity, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        plan_id,
        line_key,
        query,
        display_name,
        quantity_needed,
        cart_quantity,
        _now(),
    )


async def update_match(db: D1, match_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in fields)
    await db.run(
        f"UPDATE product_matches SET {cols} WHERE id = ?",
        *[_norm(v) for v in fields.values()],
        match_id,
    )


def _norm(v: Any) -> Any:
    return (1 if v else 0) if isinstance(v, bool) else v


# --- search cache ---------------------------------------------------------


async def cache_get(db: D1, key: str) -> dict[str, Any] | None:
    return await db.first(
        "SELECT cache_key, query, response_json, fetched_at FROM search_cache "
        "WHERE cache_key = ?",
        key,
    )


async def cache_put(db: D1, key: str, query: str, response_json: str) -> None:
    now = _now()
    await db.run(
        "INSERT INTO search_cache (cache_key, query, response_json, fetched_at) "
        "VALUES (?1, ?2, ?3, ?4) "
        "ON CONFLICT(cache_key) DO UPDATE SET query = ?2, response_json = ?3, fetched_at = ?4",
        key,
        query,
        response_json,
        now,
    )


async def cache_stats(db: D1) -> dict[str, Any]:
    entries = await db.value("SELECT COUNT(*) FROM search_cache") or 0
    last = await db.value("SELECT MAX(fetched_at) FROM search_cache")
    return {"entries": int(entries), "last_fetch_at": last}
