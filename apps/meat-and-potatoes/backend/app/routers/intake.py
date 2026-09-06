from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import IntakeSession, Profile
from ..schemas import IntakeMessageIn, IntakeMessageOut
from ..services import intake_agent, llm

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    sess = db.get(IntakeSession, session_id)
    if sess is None:
        raise HTTPException(404, "no such intake session")
    return {
        "session_id": sess.id,
        "transcript": sess.transcript,
        "complete": sess.complete,
    }


@router.post("/message", response_model=IntakeMessageOut)
def post_message(body: IntakeMessageIn, db: Session = Depends(get_db)) -> IntakeMessageOut:
    session_id = body.session_id or uuid.uuid4().hex
    sess = db.get(IntakeSession, session_id)
    if sess is None:
        sess = IntakeSession(id=session_id, transcript=[], complete=False)
        db.add(sess)

    prof = db.get(Profile, 1) or Profile(id=1, data={})
    profile_data = dict(prof.data or {})

    try:
        turn = intake_agent.next_turn(
            transcript=list(sess.transcript or []),
            profile=profile_data,
            user_message=body.message,
        )
    except llm.LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    merged = intake_agent.deep_merge(profile_data, turn.get("profile_patch") or {})
    prof.data = merged
    if db.get(Profile, 1) is None:
        db.add(prof)

    sess.transcript = list(sess.transcript or []) + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": turn["assistant_message"]},
    ]
    sess.complete = bool(turn.get("complete"))
    db.commit()

    return IntakeMessageOut(
        session_id=session_id,
        assistant_message=turn["assistant_message"],
        profile=merged,
        missing_fields=turn.get("missing_fields", []),
        complete=sess.complete,
    )
