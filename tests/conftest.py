"""Shared pytest fixtures for the backend test suite.

Mocking gotcha: `query_understanding.py` and `sql_generator.py` both do
`from backend.app.services.memory.vector import query_context`, which binds a
local name in each module's own namespace. Patching
`backend.app.services.memory.vector.query_context` (the definition site) does
NOT affect those already-bound references — you must patch
`backend.app.agents.query_understanding.query_context` and
`backend.app.agents.sql_generator.query_context` directly (the import sites).
`patched_vector_context` below does this correctly; don't "simplify" it to
patch the vector module instead, or the mock silently does nothing and real
ChromaDB calls (slow, stateful) fire during tests.
"""

from __future__ import annotations

import pytest

import backend.app.agents.query_understanding as qu_module
import backend.app.agents.sql_generator as sg_module
from backend.app.services import adapter_registry
from backend.app.services.db.file_connector import FileConnector
from backend.app.services.llm_service import llm_service
from backend.app.services.memory import sessions


@pytest.fixture(scope="session")
def soundwave_connector() -> FileConnector:
    conn = FileConnector("soundwave")
    conn.connect()
    return conn


@pytest.fixture(scope="session")
def soundwave_profile(soundwave_connector: FileConnector):
    return soundwave_connector.introspect()


@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    """Point adapter_registry at a throwaway registry.json the test controls."""
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(adapter_registry, "_REGISTRY_PATH", str(registry_path))
    return registry_path


@pytest.fixture
def isolated_sessions_db(tmp_path, monkeypatch):
    """Redirect session/turn persistence to a throwaway sqlite file."""
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(sessions, "DB_PATH", str(db_path))
    sessions.init_db()
    return db_path


@pytest.fixture
def patched_llm(monkeypatch):
    """Monkeypatch the shared llm_service singleton with canned replies.

    Usage: patched_llm(["first response", "second response"]) — each call to
    llm_service.chat(...) or .chat_with_meta(...) pops the next canned reply
    in order (shared queue — both methods draw from the same list, since only
    sql_generator uses chat_with_meta while the others use chat).
    """

    def _apply(responses: list[str]):
        queue = list(responses)

        def fake_chat(messages, temperature=0.3, timeout=90):
            if not queue:
                raise AssertionError("patched_llm: ran out of canned responses")
            return queue.pop(0)

        def fake_chat_with_meta(messages, temperature=0.3, timeout=90):
            content = fake_chat(messages, temperature, timeout)
            return content, {
                "elapsed_ms": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "tokens_per_sec": None,
            }

        monkeypatch.setattr(llm_service, "chat", fake_chat)
        monkeypatch.setattr(llm_service, "chat_with_meta", fake_chat_with_meta, raising=False)

    return _apply


@pytest.fixture
def patched_vector_context(monkeypatch):
    """Patch query_context at each agent module's import site (see module docstring)."""

    def fake_query_context(question, n_results=4):
        return ["Table: tracks. Columns: track_id, title, album_id, trk_dur_ms."]

    monkeypatch.setattr(qu_module, "query_context", fake_query_context)
    monkeypatch.setattr(sg_module, "query_context", fake_query_context)


@pytest.fixture(autouse=True)
def _reset_llm_adapter_state():
    """llm_service is a process-wide singleton — never let adapter state leak across tests."""
    yield
    llm_service.unload_adapter()
