"""QueryUnderstanding — requested-output-field policy (regex safety net + LLM extraction)
and the vague-time-range safety net (deterministic ambiguity flag → clarification branch)."""

from __future__ import annotations

import json

from backend.app.agents.query_understanding import (
    VAGUE_TIME_FLAG_PREFIX,
    QueryUnderstanding,
    _detect_vague_time_range,
)
from backend.app.models.envelope import DBProfile


def make_profile() -> DBProfile:
    return DBProfile(db_name="soundwave")


def _intent_json(**overrides) -> str:
    base = {
        "entities": ["tracks"],
        "metrics": ["COUNT"],
        "filters": [],
        "requested_fields": [],
        "time_range": None,
        "ambiguity_flags": [],
        "plain_restatement": "You asked about tracks.",
    }
    base.update(overrides)
    return json.dumps(base)


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


# -- Vague-time-range safety net ---------------------------------------------------


def test_vague_last_months_flagged_even_when_llm_missed_it(patched_llm, patched_vector_context):
    """The original bug: 'the last months' was silently restated as 'the last 3 months'."""
    patched_llm([_intent_json(plain_restatement="Most reproduced songs of the last 3 months.")])
    intent = QueryUnderstanding().parse(
        "can I know the most reproduced song of the last months?", make_profile()
    )
    flags = [f for f in intent.ambiguity_flags if f.startswith(VAGUE_TIME_FLAG_PREFIX)]
    assert len(flags) == 1
    assert "last months" in flags[0]
    assert "months" in flags[0]


def test_concrete_time_ranges_do_not_flag(patched_llm, patched_vector_context):
    queries = [
        "top songs of the last 3 months",
        "top songs of last month",  # singular = concretely one month
        "top songs since January 2026",
        "top songs of this year",
    ]
    patched_llm([_intent_json() for _ in queries])
    qu = QueryUnderstanding()
    for q in queries:
        intent = qu.parse(q, make_profile())
        assert not any(
            f.startswith(VAGUE_TIME_FLAG_PREFIX) for f in intent.ambiguity_flags
        ), f"false positive on: {q}"


def test_bare_recently_flags_only_as_sole_time_constraint(patched_llm, patched_vector_context):
    patched_llm([_intent_json(), _intent_json()])
    qu = QueryUnderstanding()
    vague = qu.parse("which songs were played recently?", make_profile())
    assert any(f.startswith(VAGUE_TIME_FLAG_PREFIX) for f in vague.ambiguity_flags)
    concrete = qu.parse("which songs were played recently, since January?", make_profile())
    assert not any(f.startswith(VAGUE_TIME_FLAG_PREFIX) for f in concrete.ambiguity_flags)


def test_history_segment_does_not_retrigger_vague_time(patched_llm, patched_vector_context):
    """After the user answers the clarification, the vague phrase lives in [History] only —
    it must not send the pipeline back into the clarification loop."""
    patched_llm([_intent_json()])
    contextualised = (
        "[History]\n"
        "user: most reproduced song of the last months?\n"
        "assistant: By \"last months\", do you mean the last 3 months or the last 6 months?\n"
        "[Current] the last 3 months"
    )
    intent = QueryUnderstanding().parse(contextualised, make_profile())
    assert not any(f.startswith(VAGUE_TIME_FLAG_PREFIX) for f in intent.ambiguity_flags)


def test_llm_time_flag_is_not_duplicated(patched_llm, patched_vector_context):
    patched_llm([_intent_json(ambiguity_flags=["time range 'last months' is vague"])])
    intent = QueryUnderstanding().parse("top songs of the last months", make_profile())
    assert len(intent.ambiguity_flags) == 1  # LLM's own flag kept, no regex duplicate


def test_detector_units_and_phrases():
    assert _detect_vague_time_range("plays in the past few weeks") == ("past few weeks", "weeks")
    assert _detect_vague_time_range("signups in recent days") == ("recent days", "days")
    assert _detect_vague_time_range("revenue for the past couple of months") == (
        "past couple of months",
        "months",
    )
    assert _detect_vague_time_range("top songs lately") == ("lately", "months")
    assert _detect_vague_time_range("top songs of the last 6 months") is None
    assert _detect_vague_time_range("how many tracks are there") is None
