from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PantryItem
from ..schemas import PantryItemIn, PantryItemOut

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: Session = Depends(get_db)) -> list[PantryItemOut]:
    rows = db.scalars(select(PantryItem).order_by(PantryItem.name)).all()
    return [PantryItemOut(id=r.id, name=r.name) for r in rows]


@router.post("", response_model=PantryItemOut)
def add_pantry(body: PantryItemIn, db: Session = Depends(get_db)) -> PantryItemOut:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "name required")
    existing = db.scalar(select(PantryItem).where(PantryItem.name == name))
    if existing:
        return PantryItemOut(id=existing.id, name=existing.name)
    row = PantryItem(name=name)
    db.add(row)
    db.commit()
    return PantryItemOut(id=row.id, name=row.name)


@router.delete("/{item_id}")
def delete_pantry(item_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(PantryItem, item_id)
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}
