"""Session routes — list, get, and create sessions."""

from fastapi import APIRouter, HTTPException

from backend.app.services.memory.sessions import (
    create_session,
    get_session,
    list_sessions,
)
from backend.app.services.orchestrator import orchestrator

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
def session_create(db_name: str | None = None, title: str = ""):
    resolved = db_name or orchestrator._active_db_name or ""
    sid = create_session(db_name=resolved, title=title)
    return {"session_id": sid}
