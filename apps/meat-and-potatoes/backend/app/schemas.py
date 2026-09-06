"""Pydantic request/response models and the meal-plan JSON schema."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- intake -------------------------------------------------------------------


class IntakeMessageIn(BaseModel):
    session_id: str | None = None
    message: str


class IntakeMessageOut(BaseModel):
    session_id: str
    assistant_message: str
    profile: dict[str, Any]
    missing_fields: list[str] = Field(default_factory=list)
    complete: bool = False


# --- profile ----------------------------------------------------------------


class ProfileOut(BaseModel):
    data: dict[str, Any]


class ProfileIn(BaseModel):
    data: dict[str, Any]


# --- plan -----------------------------------------------------------------


class PlanGenerateIn(BaseModel):
    prompt: str = ""
    days: int = 7
    meals_per_day: list[str] = Field(default_factory=lambda: ["breakfast", "lunch", "dinner"])


class IngredientOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    category: str
    staple: bool


class MealOut(BaseModel):
    id: int
    day: str
    day_index: int
    slot: str
    title: str
    description: str
    servings: int
    approx_calories: int | None
    ingredients: list[IngredientOut]


class PlanOut(BaseModel):
    id: int
    prompt: str
    notes: str
    days: int
    created_at: str
    meals: list[MealOut]


# --- pantry ---------------------------------------------------------------


class PantryItemIn(BaseModel):
    name: str


class PantryItemOut(BaseModel):
    id: int
    name: str


# --- grocery ------------------------------------------------------------------


class ShoppingLine(BaseModel):
    line_key: str
    name: str
    quantity: float
    unit: str
    category: str


class ProductMatchOut(BaseModel):
    id: int
    line_key: str
    query: str
    display_name: str
    quantity_needed: float
    item_id: str | None
    product_name: str | None
    price: float | None
    in_stock: bool
    image_url: str | None
    product_url: str | None
    seller: str | None
    cart_quantity: int
    manual: bool
    search_url: str | None = None


class GroceryListOut(BaseModel):
    plan_id: int
    provider: str
    lines: list[ShoppingLine]
    matches: list[ProductMatchOut]
    estimated_total: float | None = None


class MatchRequestIn(BaseModel):
    plan_id: int
    force: bool = False


class CartLinkIn(BaseModel):
    plan_id: int
    chunk_size: int = 1  # items per addToCart link; 1 = one at a time


class MatchOverrideIn(BaseModel):
    item_id: str | None = None
    query: str | None = None
    cart_quantity: int | None = None


class CartStep(BaseModel):
    index: int  # 1-based position in the sequence
    total: int  # total number of steps
    label: str
    url: str
    item_ids: list[str]
    quantity: int  # total units added by this step


class CartLinkOut(BaseModel):
    url: str  # all-in-one link (kept as a fallback; unreliable for big carts)
    item_count: int
    missing: list[str] = Field(default_factory=list)
    steps: list[CartStep] = Field(default_factory=list)
    warning: str | None = None  # e.g. "these are mock IDs, not real Walmart items"


class CacheStatsOut(BaseModel):
    entries: int
    hits: int
    misses: int
    last_fetch_at: str | None


# --- LLM meal-plan schema (passed to Ollama `format`) ------------------------

MEAL_PLAN_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string"},
                    "meals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slot": {"type": "string"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "servings": {"type": "integer"},
                                "approx_calories": {"type": "integer"},
                                "ingredients": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "quantity": {"type": "number"},
                                            "unit": {"type": "string"},
                                            "category": {"type": "string"},
                                            "staple": {"type": "boolean"},
                                        },
                                        "required": ["name", "quantity", "unit"],
                                    },
                                },
                            },
                            "required": ["slot", "title", "ingredients"],
                        },
                    },
                },
                "required": ["day", "meals"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["days"],
}

INTAKE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "assistant_message": {"type": "string"},
        "profile_patch": {"type": "object"},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "complete": {"type": "boolean"},
    },
    "required": ["assistant_message", "profile_patch", "complete"],
}
