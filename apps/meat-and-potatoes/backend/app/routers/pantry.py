from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import store
from ..d1 import D1, get_db
from ..schemas import PantryItemIn, PantryItemOut

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemOut])
async def list_pantry(db: D1 = Depends(get_db)) -> list[PantryItemOut]:
    rows = await store.list_pantry(db)
    return [PantryItemOut(id=r["id"], name=r["name"]) for r in rows]


@router.post("", response_model=PantryItemOut)
async def add_pantry(body: PantryItemIn, db: D1 = Depends(get_db)) -> PantryItemOut:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "name required")
    row = await store.add_pantry(db, name)
    return PantryItemOut(id=row["id"], name=row["name"])


@router.delete("/{item_id}")
async def delete_pantry(item_id: int, db: D1 = Depends(get_db)) -> dict:
    await store.delete_pantry(db, item_id)
    return {"ok": True}
