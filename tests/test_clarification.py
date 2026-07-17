"""Clarification — deterministic canned question for the vague-time flag (no LLM call),
LLM fallback preserved for every other ambiguity flavor."""

from __future__ import annotations

from backend.app.agents.clarification import Clarification
from backend.app.models.envelope import Intent


def test_vague_time_flag_gets_canned_question_without_llm(patched_llm):
    patched_llm([])  # any LLM call would raise "ran out of canned responses"
    intent = Intent(
        raw_query="can I know the most reproduced song of the last months?",
        ambiguity_flags=["vague time range: 'last months' does not specify how many months"],
    )
    question = Clarification().generate_question(intent)
    assert question == 'By "last months", do you mean the last 3 months or the last 6 months?'


def test_canned_question_adapts_unit(patched_llm):
    patched_llm([])
    intent = Intent(
        raw_query="plays in the past few weeks",
        ambiguity_flags=["vague time range: 'past few weeks' does not specify how many weeks"],
    )
    question = Clarification().generate_question(intent)
    assert question == 'By "past few weeks", do you mean the last 3 weeks or the last 6 weeks?'


def test_non_time_flags_still_use_llm(patched_llm):
    canned = "Did you mean the artist's name or the album's name?"
    patched_llm([canned])
    intent = Intent(
        raw_query="what is the name?",
        ambiguity_flags=["column 'name' exists in multiple tables"],
    )
    assert Clarification().generate_question(intent) == canned
