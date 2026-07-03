"""Orchestrator routing: clarification branch, repair loop, adapter-label wiring.

Canned LLM responses must match each agent's exact parse format or they'll
silently fall into that agent's "best-effort" fallback branch and the test
will pass for the wrong reason: query_understanding expects JSON (optionally
markdown-fenced) matching the Intent schema; sql_generator expects a
"### Rationale\\n...\\n### SQL\\n```sql\\n...\\n```" block.
"""

from __future__ import annotations

import pytest

from backend.app.models.envelope import AgentEvent, QueryResult
from backend.app.services.orchestrator import Orchestrator

VALID_INTENT_JSON = """{
  "entities": ["tracks"],
  "metrics": [],
  "filters": ["standalone singles"],
  "time_range": null,
  "ambiguity_flags": [],
  "plain_restatement": "You asked how many tracks are standalone singles."
}"""

AMBIGUOUS_INTENT_JSON = """{
  "entities": ["name"],
  "metrics": [],
  "filters": [],
  "time_range": null,
  "ambiguity_flags": ["column 'name' exists in multiple tables"],
  "plain_restatement": "You asked about a name."
}"""

VALID_SQL_RESPONSE = """### Rationale
Standalone singles are tracks with no album (EC-03: album_id IS NULL).

### SQL
```sql
SELECT COUNT(*) AS single_count FROM tracks WHERE album_id IS NULL;
```
"""

BAD_NULL_SQL_RESPONSE = """### Rationale
Filtering tracks with no album.

### SQL
```sql
SELECT track_id FROM tracks WHERE album_id = NULL;
```
"""


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


async def _run_collect(orch: Orchestrator, query: str):
    events: list[AgentEvent] = []
    result: QueryResult | None = None
    async for item in orch.run(query, session_id=None):
        if isinstance(item, QueryResult):
            result = item
        else:
            events.append(item)
    return events, result


async def test_no_database_selected_yields_clean_error():
    orch = Orchestrator()
    events, result = await _run_collect(orch, "Show me all artists.")
    assert any(e.status == "error" for e in events)
    assert result is not None
    assert result.error is not None


async def test_clarification_branch_stops_before_sql_generation(wired_orchestrator, patched_llm):
    patched_llm([AMBIGUOUS_INTENT_JSON, "Did you mean the artist's name or the album's name?"])

    events, result = await _run_collect(wired_orchestrator, "What is the name?")

    clar_events = [e for e in events if e.agent == "clarification"]
    assert any(e.status == "started" for e in clar_events)
    assert any(e.status == "done" for e in clar_events)
    assert not any(e.agent == "sql_generator" for e in events)

    started = next(e for e in clar_events if e.status == "started")
    assert started.payload is not None
    assert "adapter" in started.payload

    assert result is not None
    assert result.teaching_summary.startswith("**Clarification needed:**")


async def test_repair_loop_fixes_equals_null(wired_orchestrator, patched_llm):
    patched_llm([VALID_INTENT_JSON, BAD_NULL_SQL_RESPONSE])

    events, result = await _run_collect(
        wired_orchestrator, "How many tracks are standalone singles?"
    )

    repair_events = [
        e
        for e in events
        if e.agent == "verification"
        and e.status == "progress"
        and e.message.startswith("Repair applied:")
    ]
    assert repair_events, "expected a verification repair-applied progress event"

    assert result is not None
    assert result.sql is not None
    assert "IS NULL" in result.sql.sql.upper()
    assert result.error is None


async def test_adapter_labels_present_on_started_events(wired_orchestrator, patched_llm):
    patched_llm([VALID_INTENT_JSON, VALID_SQL_RESPONSE])

    events, result = await _run_collect(
        wired_orchestrator, "How many tracks are standalone singles?"
    )

    for agent_name in ("query_understanding", "sql_generator", "verification"):
        started = next(e for e in events if e.agent == agent_name and e.status == "started")
        assert started.payload is not None
        assert "adapter" in started.payload

    assert result is not None
    assert result.error is None
    assert result.row_count >= 1
