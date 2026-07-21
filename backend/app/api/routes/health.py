"""GET /health — liveness probe and run-environment disclosure.

The second job matters for benchmarking. EVALUATION_PROTOCOL.md §1.1 voids any
run executed without a frozen clock, and §1.3 permits a single scored run only
under greedy decoding — but both settings live in *this* process, while the
harness that scores the run is an HTTP client. A harness checking its own
environment would prove nothing about the process that actually generated the
SQL. These fields let it read the conditions off the server it is measuring and
refuse to write a report when they are not met.
"""

from fastapi import APIRouter

from backend.app.config import settings
from backend.app.services.llm_service import llm_service
from backend.app.services.orchestrator import orchestrator

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm_healthy": llm_service.is_healthy(),
        # -- run environment (EVALUATION_PROTOCOL.md §1.1–§1.3) ---------------
        "freeze_now": settings.freeze_now or None,
        "greedy": settings.greedy,
        "greedy_seed": settings.greedy_seed if settings.greedy else None,
        "connector": settings.connector,
        "constrained_planning": settings.constrained_planning,
        "active_db": orchestrator.active_db_name,
    }
