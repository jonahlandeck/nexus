from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Profile
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get(db: Session) -> Profile:
    prof = db.get(Profile, 1)
    if prof is None:
        prof = Profile(id=1, data={})
        db.add(prof)
        db.commit()
    return prof


@router.get("", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)) -> ProfileOut:
    return ProfileOut(data=_get(db).data or {})


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, db: Session = Depends(get_db)) -> ProfileOut:
    prof = _get(db)
    prof.data = body.data or {}
    db.commit()
    return ProfileOut(data=prof.data)
