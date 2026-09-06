from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import store
from ..d1 import D1, get_db
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def read_profile(db: D1 = Depends(get_db)) -> ProfileOut:
    return ProfileOut(data=await store.get_profile(db))


@router.put("", response_model=ProfileOut)
async def update_profile(body: ProfileIn, db: D1 = Depends(get_db)) -> ProfileOut:
    return ProfileOut(data=await store.set_profile(db, body.data or {}))
