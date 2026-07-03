"""VerificationAgent: 3-layer chain (syntax -> semantic -> sanity) + repair loop.

verify() calls no LLM (pure sqlglot/regex against the schema), so these tests
run against the real soundwave connector/profile with no mocking needed.
"""

from __future__ import annotations

from backend.app.agents.verification import VerificationAgent
from backend.app.models.envelope import SqlCandidate


def _agent(soundwave_connector) -> VerificationAgent:
    return VerificationAgent(soundwave_connector)


def test_valid_query_passes_all_three_layers(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT track_id, title FROM tracks WHERE album_id IS NULL;")
    report = agent.verify(candidate, soundwave_profile)
    assert report.syntax.passed
    assert report.semantic.passed
    assert report.sanity.passed
    assert report.overall_passed


def test_syntax_layer_rejects_garbage_sql(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT FROM WHERE this is not sql")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.syntax.passed
    assert not report.overall_passed


def test_hallucinated_table_is_rejected(soundwave_connector, soundwave_profile):
    # Caught by the syntax layer's EXPLAIN QUERY PLAN probe against the real
    # engine (a nonexistent table can't be planned) — semantic never runs.
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT * FROM not_a_real_table;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.syntax.passed
    assert not report.overall_passed


def test_semantic_layer_rejects_hallucinated_column(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT tracks.not_a_real_column FROM tracks;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.semantic.passed


def test_sanity_layer_rejects_non_select(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="DELETE FROM tracks;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.sanity.passed
    assert "read-only" in report.sanity.message.lower()


def test_sanity_layer_rejects_aggregate_in_where(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT album_id FROM tracks WHERE COUNT(track_id) > 1;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.sanity.passed


def test_equals_null_fails_and_proposes_is_null_repair(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT track_id FROM tracks WHERE album_id = NULL;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.sanity.passed
    assert not report.overall_passed
    assert report.repaired_sql is not None
    assert "IS NULL" in report.repaired_sql.upper()

    # Re-verifying the repaired SQL should now pass all three layers (the
    # orchestrator's repair loop relies on exactly this behavior).
    repaired = SqlCandidate(sql=report.repaired_sql)
    repaired_report = agent.verify(repaired, soundwave_profile)
    assert repaired_report.overall_passed
