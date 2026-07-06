"""QueryUnderstanding — requested-output-field policy (regex safety net + LLM extraction)."""

from __future__ import annotations

import json

from backend.app.agents.query_understanding import QueryUnderstanding
from backend.app.models.envelope import DBProfile


def make_profile() -> DBProfile:
    return DBProfile(db_name="soundwave")


def test_regex_recovers_trailing_field_the_llm_dropped(patched_llm, patched_vector_context):
    patched_llm(
        [
            json.dumps(
                {
                    "entities": ["artists"],
                    "metrics": ["TOP"],
                    "filters": [],
                    "requested_fields": [],
                    "time_range": None,
                    "ambiguity_flags": [],
                    "plain_restatement": "You asked for the top 10 artists.",
                }
            )
        ]
    )
    intent = QueryUnderstanding().parse(
        "What are the top 10 artists? give me the names", make_profile()
    )
    assert "names" in [f.lower() for f in intent.requested_fields]
    assert "names" in [e.lower() for e in intent.entities]
    assert "names" in intent.plain_restatement.lower()


def test_llm_provided_requested_fields_pass_through(patched_llm, patched_vector_context):
    patched_llm(
        [
            json.dumps(
                {
                    "entities": ["users"],
                    "metrics": [],
                    "filters": [],
                    "requested_fields": ["emails"],
                    "time_range": None,
                    "ambiguity_flags": [],
                    "plain_restatement": "You asked for the emails of banned users.",
                }
            )
        ]
    )
    intent = QueryUnderstanding().parse("show me the emails of banned users", make_profile())
    assert intent.requested_fields == ["emails"]
    assert "emails" in intent.plain_restatement.lower()


def test_no_trailing_clause_yields_no_requested_fields(patched_llm, patched_vector_context):
    patched_llm(
        [
            json.dumps(
                {
                    "entities": ["tracks"],
                    "metrics": ["COUNT"],
                    "filters": [],
                    "requested_fields": [],
                    "time_range": None,
                    "ambiguity_flags": [],
                    "plain_restatement": "You asked how many tracks exist.",
                }
            )
        ]
    )
    intent = QueryUnderstanding().parse("how many tracks are there", make_profile())
    assert intent.requested_fields == []
