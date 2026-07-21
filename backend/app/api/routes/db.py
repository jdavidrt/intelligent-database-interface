"""Database routes — list available databases, select one, get the active profile."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.db.discovery import list_available_databases
from backend.app.services.memory.sessions import list_sessions
from backend.app.services.orchestrator import orchestrator

router = APIRouter()


@router.get("/db/profile")
def db_profile():
    if orchestrator._db_profile is None:
        raise HTTPException(
            status_code=404, detail="DBProfile not loaded yet. Select a database first."
        )
    return orchestrator._db_profile.model_dump(mode="json")


@router.get("/db/list")
def db_list():
    return {"databases": [d.model_dump() for d in list_available_databases()]}


class SelectDatabaseRequest(BaseModel):
    db_name: str


@router.post("/db/select")
def db_select(req: SelectDatabaseRequest):
    try:
        profile = orchestrator.select_database(req.db_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return profile.model_dump(mode="json")


@router.get("/db/last-used")
def db_last_used():
    recent = list_sessions(limit=1)
    return {"db_name": recent[0]["db_name"] if recent else None}
