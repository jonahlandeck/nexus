"""Conversational diet / health-goal intake.

Each turn is a single JSON generation that returns the next thing to say to the
user, a patch to merge into the stored profile, and whether we have enough to
build a plan.
"""
from __future__ import annotations

from typing import Any

from . import llm
from ..config import Settings
from ..schemas import INTAKE_JSON_SCHEMA

CHECKLIST = [
    "dietary_pattern",          # omnivore / vegetarian / vegan / pescatarian / keto / paleo / ...
    "allergies",                # list, e.g. peanuts, shellfish, gluten
    "dislikes",                 # foods to avoid by preference
    "cuisines",                 # liked cuisines
    "health_goals",             # fat loss / muscle gain / maintenance / heart / low-sodium / diabetic-friendly / energy
    "target_calories",          # optional int per day
    "macros",                   # optional {protein_g, carbs_g, fat_g} or free text
    "household_size",           # people to cook for
    "servings_per_meal",        # default = household_size
    "weekly_budget_usd",        # optional
    "cook_time_minutes",        # typical time willing to spend
    "cooking_skill",            # beginner / comfortable / advanced
    "equipment",                # oven, stovetop, air fryer, instant pot, blender, ...
    "meals_per_day",            # which slots to plan: breakfast/lunch/dinner/snack
    "leftovers_ok",             # bool - happy to batch-cook & repeat
]

SYSTEM_PROMPT = f"""You are the intake assistant for "Meat And Potatoes", a weekly meal-planning app.
Your job: interview the user about their diet and health goals so the planner can build a good week of meals.

Cover these fields over the conversation (ask about what is still missing, a few at a time, conversationally):
{", ".join(CHECKLIST)}.

Rules:
- Ask at most 2-3 short questions per turn. Be warm and brief. No walls of text.
- Infer sensible values when the user is vague (e.g. servings_per_meal defaults to household_size).
- If the user gives a free-text prompt about what they want this week, capture it under profile_patch.week_prompt.
- Never invent allergies or restrictions the user did not state.
- Set "complete": true once dietary_pattern, allergies, health_goals, household_size, meals_per_day
  and cook_time_minutes are known (other fields are nice-to-have). When complete, your
  assistant_message should confirm the summary and tell them they can generate their plan.

Reply format: a single JSON object with keys:
  assistant_message (string, what to say next),
  profile_patch (object, only the fields you learned or refined this turn; may be empty),
  missing_fields (array of field names still unknown),
  complete (boolean).
"""


def _summarize_profile(profile: dict[str, Any]) -> str:
    if not profile:
        return "(nothing known yet)"
    return "\n".join(f"- {k}: {v}" for k, v in profile.items())


async def next_turn(
    transcript: list[dict[str, str]],
    profile: dict[str, Any],
    user_message: str,
    cfg: Settings | None = None,
) -> dict[str, Any]:
    """Run one intake turn. `transcript` is prior [{role, content}] user/assistant pairs."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append(
        {
            "role": "system",
            "content": "Profile known so far:\n" + _summarize_profile(profile),
        }
    )
    messages.extend(transcript)
    messages.append({"role": "user", "content": user_message})

    out = await llm.generate_json(messages, cfg, schema=INTAKE_JSON_SCHEMA)
    out.setdefault("assistant_message", "Could you tell me a bit more?")
    out.setdefault("profile_patch", {})
    out.setdefault("missing_fields", [k for k in CHECKLIST if k not in profile])
    out.setdefault("complete", False)
    return out


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into base (recursively for nested dicts). Lists are replaced."""
    result = dict(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
