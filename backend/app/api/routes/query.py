"""POST /query — main entry point."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from backend.app.services.orchestrator import orchestrator
from backend.app.models.envelope import AgentEvent, QueryResult

router = APIRouter()


class QueryRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/query")
async def query(req: QueryRequest):
    """
    Run the 7-agent pipeline and stream NDJSON.
    Each line is either an AgentEvent or the final QueryResult (type='result').
    """
    async def _stream():
        async for event in orchestrator.run(req.message, req.session_id):
            if isinstance(event, AgentEvent):
                line = event.model_dump_json() + "\n"
            elif isinstance(event, QueryResult):
                data = event.model_dump()
                data["type"] = "result"
                line = json.dumps(data, default=str) + "\n"
            else:
                line = json.dumps({"raw": str(event)}) + "\n"
            yield line

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
