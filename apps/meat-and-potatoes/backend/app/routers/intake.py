from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from .. import store
from ..config import Settings
from ..d1 import D1, get_config, get_db
from ..schemas import IntakeMessageIn, IntakeMessageOut
from ..services import intake_agent, llm

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.get("/{session_id}")
async def get_session(session_id: str, db: D1 = Depends(get_db)) -> dict:
    sess = await store.get_intake(db, session_id)
    if sess is None:
        raise HTTPException(404, "no such intake session")
    return sess


@router.post("/message", response_model=IntakeMessageOut)
async def post_message(
    body: IntakeMessageIn,
    db: D1 = Depends(get_db),
    cfg: Settings = Depends(get_config),
) -> IntakeMessageOut:
    session_id = body.session_id or uuid.uuid4().hex
    sess = await store.get_intake(db, session_id)
    transcript = list(sess["transcript"]) if sess else []

    profile_data = await store.get_profile(db)

    try:
        turn = await intake_agent.next_turn(
            transcript=transcript,
            profile=profile_data,
            user_message=body.message,
            cfg=cfg,
        )
    except llm.LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    merged = intake_agent.deep_merge(profile_data, turn.get("profile_patch") or {})
    await store.set_profile(db, merged)

    transcript = transcript + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": turn["assistant_message"]},
    ]
    complete = bool(turn.get("complete"))
    await store.save_intake(db, session_id, transcript, complete)

    return IntakeMessageOut(
        session_id=session_id,
        assistant_message=turn["assistant_message"],
        profile=merged,
        missing_fields=turn.get("missing_fields", []),
        complete=complete,
    )
