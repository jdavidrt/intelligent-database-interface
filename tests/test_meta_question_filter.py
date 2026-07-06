"""MetaQuestionFilter — heuristic + LLM-fallback detection, DBProfile-grounded answers."""

from __future__ import annotations

import pytest

from backend.app.agents.clarification import (
    META_ANSWER_PROMPT,
    SQL_KNOWLEDGE_PROMPT,
    MetaQuestionFilter,
)
from backend.app.models.envelope import ColumnInfo, DBProfile, TableInfo


def make_profile() -> DBProfile:
    return DBProfile(
        db_name="soundwave",
        domain_description="A music streaming service's catalog and listening activity.",
        tables=[
            TableInfo(
                name="tracks",
                description="Individual songs available in the catalog.",
                columns=[ColumnInfo(name="track_id", data_type="INTEGER", is_nullable=False)],
            )
        ],
    )


def _capture_llm(monkeypatch, reply: str = "ok") -> list:
    """Patch llm_service.chat to record the messages each branch passes it and return a
    canned reply, so a test can assert *which* branch ran (by system prompt) and that the
    DB facts reached the prompt."""
    from backend.app.services.llm_service import llm_service

    calls: list = []

    def fake_chat(messages, temperature=0.3, timeout=90):
        calls.append(messages)
        return reply

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    return calls


def test_sql_signal_short_circuits_without_llm_call(patched_llm):
    patched_llm([])  # any chat() call would raise "ran out of canned responses"
    f = MetaQuestionFilter()
    assert f.is_meta_question("How many tracks are there?", make_profile()) is False


def test_meta_regex_short_circuits_without_llm_call(patched_llm):
    patched_llm([])
    f = MetaQuestionFilter()
    profile = make_profile()
    assert f.is_meta_question("What is this database about?", profile) is True
    assert f.is_meta_question("What can you do?", profile) is True


def test_offtopic_phrasing_not_covered_by_regex_is_caught_by_allowlist_gate(patched_llm):
    # Regression test: "how is the weather" doesn't match _PERSONAL_OFFTOPIC_RE (which only
    # had "what's/what is the weather"), but it isn't DB-related or SQL-knowledge either, so
    # the allowlist gate must catch it deterministically -- no LLM call needed at all.
    patched_llm([])
    f = MetaQuestionFilter()
    assert f.is_meta_question("How is the weather today?", make_profile()) is True


def test_sql_knowledge_question_short_circuits_without_llm_call(patched_llm):
    patched_llm([])
    f = MetaQuestionFilter()
    assert f.is_meta_question("What is a JOIN in SQL?", make_profile()) is True


def test_ambiguous_db_related_phrasing_falls_back_to_llm_classification(patched_llm):
    patched_llm(["YES"])
    f = MetaQuestionFilter()
    assert f.is_meta_question("Tell me something about tracks", make_profile()) is True


def test_classification_failure_defaults_to_not_meta(monkeypatch):
    from backend.app.services.llm_service import llm_service

    def raise_chat(messages, temperature=0.3, timeout=90):
        raise ConnectionError("no server")

    monkeypatch.setattr(llm_service, "chat", raise_chat)
    f = MetaQuestionFilter()
    assert f.is_meta_question("Tell me something about tracks", make_profile()) is False


def test_answer_is_grounded_in_profile_facts(patched_llm):
    patched_llm(["Soundwave tracks a music catalog. Try asking about top artists."])
    f = MetaQuestionFilter()
    answer = f.answer("What is this database about?", make_profile())
    assert answer == "Soundwave tracks a music catalog. Try asking about top artists."


def test_personal_regex_short_circuits_without_llm_call(patched_llm):
    patched_llm([])
    f = MetaQuestionFilter()
    profile = make_profile()
    assert f.is_meta_question("How are you today?", profile) is True
    assert f.is_meta_question("Who are you?", profile) is True
    assert f.is_meta_question("Are you christian?", profile) is True


def test_offtopic_regex_short_circuits_without_llm_call(patched_llm):
    patched_llm([])
    f = MetaQuestionFilter()
    profile = make_profile()
    assert f.is_meta_question("What's the weather today?", profile) is True
    assert f.is_meta_question("What is the price of the dollar today?", profile) is True


def test_personal_question_routes_to_offtopic_redirect_not_db_facts(patched_llm):
    patched_llm(["I'm just a database assistant — ask me about soundwave instead!"])
    f = MetaQuestionFilter()
    answer = f.answer("How are you today?", make_profile())
    assert answer == "I'm just a database assistant — ask me about soundwave instead!"


def test_offtopic_question_routes_to_redirect_not_db_facts(patched_llm):
    patched_llm(["I can't check the weather, but I can help with soundwave's data!"])
    f = MetaQuestionFilter()
    answer = f.answer("What's the weather today?", make_profile())
    assert answer == "I can't check the weather, but I can help with soundwave's data!"


# -- DB-identity questions: the regression case from the audit -------------------------
# "What is the name of the database we are on now?" used to fall through the bare word
# "database" into the generic SQL-knowledge branch and get a context-less "SELECT
# DATABASE()" reply. It must now be recognized deterministically and answered from
# DBProfile facts.
DB_IDENTITY_QUESTIONS = [
    "What is the name of the database we are on now?",
    "Which database are we on?",
    "What database is this?",
    "What's the current database?",
    "What database am I connected to?",
]


@pytest.mark.parametrize("question", DB_IDENTITY_QUESTIONS)
def test_db_identity_question_is_detected_as_meta_without_llm(patched_llm, question):
    patched_llm([])  # detection must be regex-only — any chat() call would raise
    f = MetaQuestionFilter()
    assert f.is_meta_question(question, make_profile()) is True


@pytest.mark.parametrize("question", DB_IDENTITY_QUESTIONS)
def test_db_identity_question_routes_to_grounded_system_answer(monkeypatch, question):
    calls = _capture_llm(monkeypatch, reply="You're connected to soundwave.")
    f = MetaQuestionFilter()
    answer = f.answer(question, make_profile())
    assert answer == "You're connected to soundwave."
    assert len(calls) == 1
    system_prompt, user_msg = calls[0][0]["content"], calls[0][1]["content"]
    # grounded "about this system" branch, NOT the generic SQL-knowledge branch
    assert system_prompt == META_ANSWER_PROMPT
    # and the database's real name reached the prompt
    assert "soundwave" in user_msg


def test_sql_knowledge_question_routes_to_sql_branch_grounded_with_db_example(monkeypatch):
    # "What is a JOIN?" still routes to the SQL-knowledge branch (not the system branch),
    # but that branch is now grounded: the connected DB's real tables reach the prompt so
    # the concept is illustrated with them rather than a textbook example.
    calls = _capture_llm(monkeypatch, reply="A JOIN combines rows from two tables.")
    f = MetaQuestionFilter()
    answer = f.answer("What is a JOIN in SQL?", make_profile())
    assert answer == "A JOIN combines rows from two tables."
    assert len(calls) == 1
    system_prompt, user_msg = calls[0][0]["content"], calls[0][1]["content"]
    assert system_prompt == SQL_KNOWLEDGE_PROMPT  # not META_ANSWER_PROMPT
    assert "tracks" in user_msg  # a real table name is now available to illustrate with
