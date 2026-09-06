from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import store
from ..config import Settings
from ..d1 import D1, get_config, get_db
from ..schemas import PlanGenerateIn, PlanOut
from ..services import llm, planner

router = APIRouter(prefix="/api/plan", tags=["plan"])

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def serialize_plan(plan: dict) -> PlanOut:
    return PlanOut.model_validate(plan)


async def _plan_or_404(db: D1, plan_id: int) -> dict:
    plan = await store.get_plan_full(db, plan_id)
    if plan is None:
        raise HTTPException(404, "no such plan")
    return plan


@router.post("/generate", response_model=PlanOut)
async def generate(
    body: PlanGenerateIn,
    db: D1 = Depends(get_db),
    cfg: Settings = Depends(get_config),
) -> PlanOut:
    profile_data = await store.get_profile(db)

    try:
        raw = await planner.generate_plan_json(
            profile=profile_data,
            prompt=body.prompt,
            days=body.days,
            meals_per_day=body.meals_per_day,
            cfg=cfg,
        )
    except llm.LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    meals: list[dict] = []
    for di, day in enumerate(raw.get("days", [])):
        day_label = str(day.get("day") or (_WEEKDAYS[di] if di < 7 else f"Day {di + 1}"))
        for meal in day.get("meals", []):
            meals.append(
                {
                    "day": day_label,
                    "day_index": di,
                    "slot": str(meal.get("slot", "meal")),
                    "title": str(meal.get("title", "Untitled")),
                    "description": str(meal.get("description", "") or ""),
                    "servings": int(meal.get("servings", 1) or 1),
                    "approx_calories": _opt_int(meal.get("approx_calories")),
                    "ingredients": [
                        {
                            "name": str(ing.get("name", "")).strip(),
                            "quantity": _num(ing.get("quantity")),
                            "unit": str(ing.get("unit", "") or ""),
                            "category": str(ing.get("category", "") or ""),
                            "staple": bool(ing.get("staple", False)),
                        }
                        for ing in meal.get("ingredients", [])
                    ],
                }
            )

    plan_id = await store.create_plan(
        db,
        prompt=body.prompt,
        profile_snapshot=profile_data,
        notes=str(raw.get("notes", "") or ""),
        days=body.days,
        meals=meals,
    )
    return serialize_plan(await _plan_or_404(db, plan_id))


@router.get("/latest", response_model=PlanOut)
async def latest(db: D1 = Depends(get_db)) -> PlanOut:
    plan_id = await store.latest_plan_id(db)
    if plan_id is None:
        raise HTTPException(404, "no plans yet")
    return serialize_plan(await _plan_or_404(db, plan_id))


@router.get("/{plan_id}", response_model=PlanOut)
async def by_id(plan_id: int, db: D1 = Depends(get_db)) -> PlanOut:
    return serialize_plan(await _plan_or_404(db, plan_id))


def _opt_int(v) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
