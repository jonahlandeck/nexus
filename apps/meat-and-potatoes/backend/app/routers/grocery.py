from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from .. import store
from ..config import Settings
from ..d1 import D1, get_config, get_db
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
from ..services.grocery.base import (
    GroceryProviderError,
    Product,
    build_cart_link,
    build_cart_steps,
)
from ..services.grocery.factory import get_provider
from ..services.planner import consolidate, normalize_name

log = logging.getLogger("meatpotatoes.grocery")
router = APIRouter(prefix="/api/grocery", tags=["grocery"])

_COUNTABLE = {"each", "", "clove", "can", "piece", "ct", "pkg", "bunch"}


async def _lines_for_plan(db: D1, plan_id: int) -> list[dict]:
    plan = await store.get_plan_full(db, plan_id)
    if plan is None:
        raise HTTPException(404, "no such plan")
    pantry = [r["name"] for r in await store.list_pantry(db)]
    return consolidate(store.plan_to_days(plan), pantry=pantry)


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


def _product_fields(p: Product) -> dict:
    return {
        "item_id": p.item_id or None,
        "product_name": p.name,
        "price": p.price,
        "in_stock": p.in_stock,
        "image_url": p.image_url,
        "product_url": p.product_url,
        "seller": p.seller,
    }


def _match_out(m: dict, provider) -> ProductMatchOut:
    return ProductMatchOut(
        id=m["id"],
        line_key=m["line_key"],
        query=m["query"],
        display_name=m["display_name"],
        quantity_needed=m["quantity_needed"],
        item_id=m["item_id"],
        product_name=m["product_name"],
        price=m["price"],
        in_stock=m["in_stock"],
        image_url=m["image_url"],
        product_url=m["product_url"],
        seller=m["seller"],
        cart_quantity=m["cart_quantity"],
        manual=m["manual"],
        search_url=provider.search_url(m["query"]),
    )


@router.get("/list/{plan_id}", response_model=GroceryListOut)
async def grocery_list(
    plan_id: int, db: D1 = Depends(get_db), cfg: Settings = Depends(get_config)
) -> GroceryListOut:
    provider = get_provider(cfg)
    lines = await _lines_for_plan(db, plan_id)
    by_key = {m["line_key"]: m for m in await store.matches_for_plan(db, plan_id)}
    ordered = [by_key[l["line_key"]] for l in lines if l["line_key"] in by_key]
    total = (
        sum((m["price"] or 0) * m["cart_quantity"] for m in ordered if m["item_id"])
        or None
    )
    return GroceryListOut(
        plan_id=plan_id,
        provider=provider.name,
        lines=[ShoppingLine(**l) for l in lines],
        matches=[_match_out(m, provider) for m in ordered],
        estimated_total=round(total, 2) if total else None,
    )


@router.post("/match", response_model=GroceryListOut)
async def match(
    body: MatchRequestIn,
    db: D1 = Depends(get_db),
    cfg: Settings = Depends(get_config),
) -> GroceryListOut:
    provider = get_provider(cfg)
    lines = await _lines_for_plan(db, body.plan_id)
    existing = {
        m["line_key"]: m for m in await store.matches_for_plan(db, body.plan_id)
    }

    for line in lines:
        m = existing.get(line["line_key"])
        if m and m["manual"] and not body.force:
            continue
        if m and m["item_id"] and not body.force:
            continue

        if m is None:
            new_id = await store.create_match(
                db,
                plan_id=body.plan_id,
                line_key=line["line_key"],
                query=line["name"],
                display_name=line["name"],
                quantity_needed=line["quantity"],
                cart_quantity=_suggested_qty(line),
            )
            m = {"id": new_id, "line_key": line["line_key"], "query": line["name"]}
            existing[line["line_key"]] = m

        try:
            results = await provider.search(m["query"], db, force=body.force)
        except GroceryProviderError as exc:
            raise HTTPException(502, str(exc)) from exc

        if results:
            best = max(results, key=lambda p: _score(p, line))
            await store.update_match(db, m["id"], **_product_fields(best))
        else:
            # links / no-hit: leave item_id None; the UI falls back to search_url
            await store.update_match(db, m["id"], product_name=None, item_id=None)

    return await grocery_list(body.plan_id, db, cfg)


@router.put("/match/{match_id}", response_model=ProductMatchOut)
async def override_match(
    match_id: int,
    body: MatchOverrideIn,
    db: D1 = Depends(get_db),
    cfg: Settings = Depends(get_config),
) -> ProductMatchOut:
    provider = get_provider(cfg)
    m = await store.get_match(db, match_id)
    if m is None:
        raise HTTPException(404, "no such match")

    fields: dict = {}
    if body.cart_quantity is not None:
        fields["cart_quantity"] = max(1, int(body.cart_quantity))

    if body.item_id is not None:
        fields["item_id"] = body.item_id.strip() or None
        fields["manual"] = True
        fields["in_stock"] = True

    if body.query is not None and body.query.strip():
        fields["query"] = body.query.strip()
        fields["manual"] = True
        try:
            results = await provider.search(fields["query"], db, force=True)
        except GroceryProviderError as exc:
            raise HTTPException(502, str(exc)) from exc
        if results:
            fields.update(_product_fields(results[0]))

    await store.update_match(db, match_id, **fields)
    return _match_out(await store.get_match(db, match_id), provider)


def _step_label(group: list[dict]) -> str:
    if len(group) == 1:
        m = group[0]
        name = m["product_name"] or m["display_name"]
        return f"{name} ×{m['cart_quantity']}" if m["cart_quantity"] > 1 else name
    return f"{len(group)} items"


@router.post("/cart-link", response_model=CartLinkOut)
async def cart_link(
    body: CartLinkIn,
    db: D1 = Depends(get_db),
    cfg: Settings = Depends(get_config),
) -> CartLinkOut:
    matches = await store.matches_for_plan(db, body.plan_id)
    # Walk the steps in the same order the grocery list shows the lines.
    try:
        order = {
            l["line_key"]: i
            for i, l in enumerate(await _lines_for_plan(db, body.plan_id))
        }
        matches.sort(key=lambda m: order.get(m["line_key"], len(order)))
    except HTTPException:
        pass

    picked = [m for m in matches if m["item_id"]]
    missing = [m["display_name"] for m in matches if not m["item_id"]]

    size = max(1, body.chunk_size)
    groups = [picked[i : i + size] for i in range(0, len(picked), size)]
    urls = build_cart_steps([(m["item_id"], m["cart_quantity"]) for m in picked], size)
    steps = [
        CartStep(
            index=i,
            total=len(groups),
            label=_step_label(group),
            url=url,
            item_ids=[m["item_id"] for m in group if m["item_id"]],
            quantity=sum(m["cart_quantity"] for m in group),
        )
        for i, (group, url) in enumerate(zip(groups, urls), start=1)
    ]
    warning = None
    if get_provider(cfg).name == "mock" and picked:
        warning = (
            "Provider is 'mock': these item IDs are placeholder hashes, not real "
            "Walmart item numbers, so this link will not add anything to a real cart. "
            "Set MAP_PROVIDER=scraperapi (or paste real Walmart item ids per line) "
            "and re-run 'Find Walmart products'."
        )

    return CartLinkOut(
        url=build_cart_link([(m["item_id"], m["cart_quantity"]) for m in picked]),
        item_count=len(picked),
        missing=missing,
        steps=steps,
        warning=warning,
    )


@router.get("/cache/stats", response_model=CacheStatsOut)
async def cache_stats(
    db: D1 = Depends(get_db), cfg: Settings = Depends(get_config)
) -> CacheStatsOut:
    provider = get_provider(cfg)
    if hasattr(provider, "stats"):
        return CacheStatsOut(**await provider.stats(db))
    return CacheStatsOut(entries=0, hits=0, misses=0, last_fetch_at=None)
