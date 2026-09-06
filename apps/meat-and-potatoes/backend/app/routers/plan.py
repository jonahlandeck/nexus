from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Ingredient, Meal, Plan, Profile
from ..schemas import IngredientOut, MealOut, PlanGenerateIn, PlanOut
from ..services import llm, planner

router = APIRouter(prefix="/api/plan", tags=["plan"])

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def serialize_plan(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        prompt=plan.prompt,
        notes=plan.notes,
        days=plan.days,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
        meals=[
            MealOut(
                id=m.id,
                day=m.day,
                day_index=m.day_index,
                slot=m.slot,
                title=m.title,
                description=m.description,
                servings=m.servings,
                approx_calories=m.approx_calories,
                ingredients=[
                    IngredientOut(
                        id=i.id,
                        name=i.name,
                        quantity=i.quantity,
                        unit=i.unit,
                        category=i.category,
                        staple=i.staple,
                    )
                    for i in m.ingredients
                ],
            )
            for m in plan.meals
        ],
    )


def plan_to_dict(plan: Plan) -> dict:
    """Rebuild the {days:[{day, meals:[{...ingredients}]}]} shape for consolidation."""
    days: dict[str, dict] = {}
    for m in plan.meals:
        day = days.setdefault(m.day, {"day": m.day, "meals": []})
        day["meals"].append(
            {
                "slot": m.slot,
                "title": m.title,
                "ingredients": [
                    {
                        "name": i.name,
                        "quantity": i.quantity,
                        "unit": i.unit,
                        "category": i.category,
                        "staple": i.staple,
                    }
                    for i in m.ingredients
                ],
            }
        )
    return {"days": list(days.values()), "notes": plan.notes}


@router.post("/generate", response_model=PlanOut)
def generate(body: PlanGenerateIn, db: Session = Depends(get_db)) -> PlanOut:
    prof = db.get(Profile, 1)
    profile_data = dict(prof.data or {}) if prof else {}

    try:
        raw = planner.generate_plan_json(
            profile=profile_data,
            prompt=body.prompt,
            days=body.days,
            meals_per_day=body.meals_per_day,
        )
    except llm.LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    plan = Plan(
        prompt=body.prompt,
        profile_snapshot=profile_data,
        notes=str(raw.get("notes", "") or ""),
        days=body.days,
    )
    db.add(plan)
    db.flush()

    for di, day in enumerate(raw.get("days", [])):
        day_label = str(day.get("day") or (_WEEKDAYS[di] if di < 7 else f"Day {di + 1}"))
        for meal in day.get("meals", []):
            m = Meal(
                plan_id=plan.id,
                day=day_label,
                day_index=di,
                slot=str(meal.get("slot", "meal")),
                title=str(meal.get("title", "Untitled")),
                description=str(meal.get("description", "") or ""),
                servings=int(meal.get("servings", 1) or 1),
                approx_calories=_opt_int(meal.get("approx_calories")),
            )
            db.add(m)
            db.flush()
            for ing in meal.get("ingredients", []):
                db.add(
                    Ingredient(
                        meal_id=m.id,
                        name=str(ing.get("name", "")).strip(),
                        quantity=_num(ing.get("quantity")),
                        unit=str(ing.get("unit", "") or ""),
                        category=str(ing.get("category", "") or ""),
                        staple=bool(ing.get("staple", False)),
                    )
                )
    db.commit()
    db.refresh(plan)
    return serialize_plan(plan)


@router.get("/latest", response_model=PlanOut)
def latest(db: Session = Depends(get_db)) -> PlanOut:
    plan = db.scalars(select(Plan).order_by(Plan.id.desc()).limit(1)).first()
    if plan is None:
        raise HTTPException(404, "no plans yet")
    return serialize_plan(plan)


@router.get("/{plan_id}", response_model=PlanOut)
def by_id(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "no such plan")
    return serialize_plan(plan)


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
