from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Plan, ProductMatch
from ..schemas import (
    CacheStatsOut,
    CartLinkIn,
    CartLinkOut,
    CartStep,
    GroceryListOut,
    MatchOverrideIn,
    MatchRequestIn,
    ProductMatchOut,
    ShoppingLine,
)
from ..services.grocery.base import Product, build_cart_link, build_cart_steps
from ..services.grocery.factory import get_provider
from ..services.grocery.base import GroceryProviderError
from ..services.planner import consolidate, normalize_name
from .plan import plan_to_dict

log = logging.getLogger("meatpotatoes.grocery")
router = APIRouter(prefix="/api/grocery", tags=["grocery"])

_COUNTABLE = {"each", "", "clove", "can", "piece", "ct", "pkg", "bunch"}


def _lines_for_plan(db: Session, plan_id: int) -> list[dict]:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "no such plan")
    from ..models import PantryItem

    pantry = [p.name for p in db.scalars(select(PantryItem)).all()]
    return consolidate(plan_to_dict(plan), pantry=pantry)


def _score(product: Product, line: dict) -> tuple:
    want = set(normalize_name(line["name"]).split())
    got = set(normalize_name(product.name).split())
    overlap = len(want & got)
    return (
        1 if product.in_stock else 0,
        overlap,
        1 if product.price is not None else 0,
        -(product.price or 9999),
    )


def _suggested_qty(line: dict) -> int:
    if line["unit"] in _COUNTABLE and line["quantity"] > 1:
        return max(1, min(12, round(line["quantity"])))
    return 1


def _match_out(m: ProductMatch, provider) -> ProductMatchOut:
    return ProductMatchOut(
        id=m.id,
        line_key=m.line_key,
        query=m.query,
        display_name=m.display_name,
        quantity_needed=m.quantity_needed,
        item_id=m.item_id,
        product_name=m.product_name,
        price=m.price,
        in_stock=m.in_stock,
        image_url=m.image_url,
        product_url=m.product_url,
        seller=m.seller,
        cart_quantity=m.cart_quantity,
        manual=m.manual,
        search_url=provider.search_url(m.query),
    )


def _apply_product(m: ProductMatch, p: Product) -> None:
    m.item_id = p.item_id or None
    m.product_name = p.name
    m.price = p.price
    m.in_stock = p.in_stock
    m.image_url = p.image_url
    m.product_url = p.product_url
    m.seller = p.seller


@router.get("/list/{plan_id}", response_model=GroceryListOut)
def grocery_list(plan_id: int, db: Session = Depends(get_db)) -> GroceryListOut:
    provider = get_provider()
    lines = _lines_for_plan(db, plan_id)
    matches = db.scalars(
        select(ProductMatch).where(ProductMatch.plan_id == plan_id)
    ).all()
    by_key = {m.line_key: m for m in matches}
    ordered = [by_key[l["line_key"]] for l in lines if l["line_key"] in by_key]
    total = sum((m.price or 0) * m.cart_quantity for m in ordered if m.item_id) or None
    return GroceryListOut(
        plan_id=plan_id,
        provider=provider.name,
        lines=[ShoppingLine(**l) for l in lines],
        matches=[_match_out(m, provider) for m in ordered],
        estimated_total=round(total, 2) if total else None,
    )


@router.post("/match", response_model=GroceryListOut)
def match(body: MatchRequestIn, db: Session = Depends(get_db)) -> GroceryListOut:
    provider = get_provider()
    lines = _lines_for_plan(db, body.plan_id)
    existing = {
        m.line_key: m
        for m in db.scalars(
            select(ProductMatch).where(ProductMatch.plan_id == body.plan_id)
        ).all()
    }

    for line in lines:
        m = existing.get(line["line_key"])
        if m and m.manual and not body.force:
            continue
        if m and m.item_id and not body.force:
            continue

        if m is None:
            m = ProductMatch(
                plan_id=body.plan_id,
                line_key=line["line_key"],
                query=line["name"],
                display_name=line["name"],
                quantity_needed=line["quantity"],
                cart_quantity=_suggested_qty(line),
            )
            db.add(m)
            existing[line["line_key"]] = m

        try:
            results = provider.search(m.query, force=body.force)
        except GroceryProviderError as exc:
            raise HTTPException(502, str(exc)) from exc

        if results:
            best = max(results, key=lambda p: _score(p, line))
            _apply_product(m, best)
        else:
            # links / no-hit: leave item_id None; the UI falls back to search_url
            m.product_name = None
            m.item_id = None

    db.commit()
    return grocery_list(body.plan_id, db)


@router.put("/match/{match_id}", response_model=ProductMatchOut)
def override_match(
    match_id: int, body: MatchOverrideIn, db: Session = Depends(get_db)
) -> ProductMatchOut:
    provider = get_provider()
    m = db.get(ProductMatch, match_id)
    if m is None:
        raise HTTPException(404, "no such match")

    if body.cart_quantity is not None:
        m.cart_quantity = max(1, int(body.cart_quantity))

    if body.item_id is not None:
        m.item_id = body.item_id.strip() or None
        m.manual = True
        m.in_stock = True

    if body.query is not None and body.query.strip():
        m.query = body.query.strip()
        m.manual = True
        try:
            results = provider.search(m.query, force=True)
        except GroceryProviderError as exc:
            raise HTTPException(502, str(exc)) from exc
        if results:
            _apply_product(m, results[0])

    db.commit()
    db.refresh(m)
    return _match_out(m, provider)


def _step_label(group: list[ProductMatch]) -> str:
    if len(group) == 1:
        m = group[0]
        name = m.product_name or m.display_name
        return f"{name} ×{m.cart_quantity}" if m.cart_quantity > 1 else name
    return f"{len(group)} items"


@router.post("/cart-link", response_model=CartLinkOut)
def cart_link(body: CartLinkIn, db: Session = Depends(get_db)) -> CartLinkOut:
    matches = list(
        db.scalars(
            select(ProductMatch).where(ProductMatch.plan_id == body.plan_id)
        ).all()
    )
    # Walk the steps in the same order the grocery list shows the lines.
    try:
        order = {
            l["line_key"]: i
            for i, l in enumerate(_lines_for_plan(db, body.plan_id))
        }
        matches.sort(key=lambda m: order.get(m.line_key, len(order)))
    except HTTPException:
        pass

    picked = [m for m in matches if m.item_id]
    missing = [m.display_name for m in matches if not m.item_id]

    size = max(1, body.chunk_size)
    groups = [picked[i : i + size] for i in range(0, len(picked), size)]
    urls = build_cart_steps([(m.item_id, m.cart_quantity) for m in picked], size)
    steps = [
        CartStep(
            index=i,
            total=len(groups),
            label=_step_label(group),
            url=url,
            item_ids=[m.item_id for m in group if m.item_id],
            quantity=sum(m.cart_quantity for m in group),
        )
        for i, (group, url) in enumerate(zip(groups, urls), start=1)
    ]
    warning = None
    if get_provider().name == "mock" and picked:
        warning = (
            "Provider is 'mock': these item IDs are placeholder hashes, not real "
            "Walmart item numbers, so this link will not add anything to a real cart. "
            "Set MAP_PROVIDER=scraperapi (or paste real Walmart item ids per line) "
            "and re-run 'Find Walmart products'."
        )

    return CartLinkOut(
        url=build_cart_link([(m.item_id, m.cart_quantity) for m in picked]),
        item_count=len(picked),
        missing=missing,
        steps=steps,
        warning=warning,
    )


@router.get("/cache/stats", response_model=CacheStatsOut)
def cache_stats() -> CacheStatsOut:
    provider = get_provider()
    if hasattr(provider, "stats"):
        return CacheStatsOut(**provider.stats())
    return CacheStatsOut(entries=0, hits=0, misses=0, last_fetch_at=None)
