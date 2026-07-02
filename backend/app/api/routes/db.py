"""GET /db/profile — return the current DBProfile."""

from fastapi import APIRouter, HTTPException
from backend.app.services.orchestrator import orchestrator

router = APIRouter()


@router.get("/db/profile")
def db_profile():
    if orchestrator._db_profile is None:
        raise HTTPException(status_code=404, detail="DBProfile not loaded yet. Run a query first.")
    return orchestrator._db_profile.model_dump(mode="json")
