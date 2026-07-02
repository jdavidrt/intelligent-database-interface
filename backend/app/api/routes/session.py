"""Session routes — list, get, and create sessions."""

from fastapi import APIRouter, HTTPException
from backend.app.services.memory.sessions import (
    list_sessions, get_session, create_session,
)

router = APIRouter()


@router.get("/session")
def sessions_list():
    return {"sessions": list_sessions()}


@router.get("/session/{session_id}")
def session_get(session_id: str):
    s = get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.post("/session")
def session_create(db_name: str = "soundwave_db", title: str = ""):
    sid = create_session(db_name=db_name, title=title)
    return {"session_id": sid}
