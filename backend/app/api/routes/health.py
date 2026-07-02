"""GET /health — liveness probe."""

from fastapi import APIRouter
from backend.app.services.llm_service import llm_service

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm_healthy": llm_service.is_healthy(),
    }
