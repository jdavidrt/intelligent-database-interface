"""KI-1 (session restore) regression tests — offline, LLM mocked.

Covers the two halves of the restore path the frontend depends on:
(a) a full /query run persists an assistant turn carrying `sql` + `rows_json`;
(b) GET /session/{id} (via `get_session`) returns turns with the exact fields
    `loadFromSession` (frontend/src/stores/queryStore.ts) consumes to rebuild
    bot messages: turn_id, role, content, sql, rows_json — including the
    clarification branch, whose assistant turn is now persisted too.

The frontend reconstruction itself is a pure mapping over these fields (no
test runner is installed in `frontend/`, and MASTERPLAN forbids new heavy
deps), so the wire contract asserted here is the load-bearing part.
"""

from __future__ import annotations

import json

import pytest
from test_orchestrator import (  # tests/ is on sys.path (pytest rootdir insertion)
    AMBIGUOUS_INTENT_JSON,
    VALID_INTENT_JSON,
    VALID_SQL_RESPONSE,
)

from backend.app.models.envelope import QueryResult
from backend.app.services.memory import sessions
from backend.app.services.orchestrator import Orchestrator


@pytest.fixture
def wired_orchestrator(
    soundwave_connector, soundwave_profile, isolated_sessions_db, patched_vector_context
):
    from backend.app.agents.verification import VerificationAgent

    orch = Orchestrator()
    orch._db = soundwave_connector
    orch._db_profile = soundwave_profile
    orch._verification = VerificationAgent(soundwave_connector)
    orch._active_db_name = "soundwave"
    return orch


async def _run_to_result(orch: Orchestrator, query: str) -> QueryResult:
    result: QueryResult | None = None
    async for item in orch.run(query, session_id=None):
        if isinstance(item, QueryResult):
            result = item
    assert result is not None
    return result


async def test_full_query_persists_assistant_turn_with_sql_and_rows(
    wired_orchestrator, patched_llm
):
    patched_llm([VALID_INTENT_JSON, VALID_SQL_RESPONSE])

    result = await _run_to_result(wired_orchestrator, "How many tracks are standalone singles?")
    assert result.error is None

    detail = sessions.get_session(result.session_id)
    assert detail is not None

    assistant_turns = [t for t in detail["turns"] if t["role"] == "assistant"]
    assert len(assistant_turns) == 1
    turn = assistant_turns[0]

    # Fields loadFromSession consumes to rebuild the restored AnswerPanel.
    assert turn["turn_id"]
    assert turn["content"] == result.teaching_summary
    assert turn["sql"] and "SELECT" in turn["sql"].upper()
    rows = json.loads(turn["rows_json"])
    assert isinstance(rows, list) and len(rows) >= 1

    # Pendiente 1: the session title is the first user question, not the default.
    assert detail["title"] == "How many tracks are standalone singles?"


async def test_restore_contract_includes_clarification_assistant_turn(
    wired_orchestrator, patched_llm
):
    # Meta filter LLM classification ("NO") → ambiguous intent → clarification question.
    patched_llm(
        ["NO", AMBIGUOUS_INTENT_JSON, "Did you mean the artist's name or the album's name?"]
    )

    result = await _run_to_result(wired_orchestrator, "What is the name?")
    assert result.teaching_summary.startswith("**Clarification needed:**")

    detail = sessions.get_session(result.session_id)
    assert detail is not None

    # Both turns present and ordered user → assistant, with every field the
    # frontend reconstruction reads (sql/rows_json legitimately null here —
    # AnswerPanel then renders the teaching summary as the whole answer).
    roles = [t["role"] for t in detail["turns"]]
    assert roles == ["user", "assistant"]
    bot = detail["turns"][1]
    for field in ("turn_id", "content", "sql", "rows_json"):
        assert field in bot
    assert bot["content"] == result.teaching_summary
    assert bot["sql"] is None
    assert bot["rows_json"] is None
