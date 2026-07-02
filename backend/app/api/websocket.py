"""WebSocket /ws — streams AgentEvents for the ProgressIndicator."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.orchestrator import orchestrator
from backend.app.models.envelope import AgentEvent, QueryResult
import json

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("message", "")
            session_id = data.get("session_id")

            async for event in orchestrator.run(query, session_id):
                if isinstance(event, AgentEvent):
                    await websocket.send_text(event.model_dump_json())
                elif isinstance(event, QueryResult):
                    payload = event.model_dump()
                    payload["type"] = "result"
                    await websocket.send_text(json.dumps(payload, default=str))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
