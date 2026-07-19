"""VerificationAgent: 3-layer chain (syntax -> semantic -> sanity) + repair loop.

verify() calls no LLM (pure sqlglot/regex against the schema), so these tests
run against the real soundwave connector/profile with no mocking needed.
"""

from __future__ import annotations

from backend.app.agents.verification import VerificationAgent
from backend.app.models.envelope import Intent, SqlCandidate


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


# -- Alias-aware schema linking (the pe.stream_count bug) ----------------------------


def test_alias_qualified_hallucinated_column_is_rejected(soundwave_connector, soundwave_profile):
    """The original bug: 'pe.stream_count' passed semantic verification because the
    alias 'pe' was never resolved to play_events — the column check was skipped and
    the bad SQL reached execution. stream_count actually lives in daily_artist_metrics
    (the EC-07 trap table)."""
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(
        sql=(
            "SELECT a.name AS artist_name, SUM(pe.stream_count) AS total_streams "
            "FROM artists a "
            "JOIN track_artists ta ON a.artist_id = ta.artist_id "
            "JOIN play_events pe ON ta.track_id = pe.track_id "
            "WHERE ta.is_prim = 1 "
            "GROUP BY a.artist_id, a.name "
            "ORDER BY total_streams DESC;"
        )
    )
    report = agent.verify(candidate, soundwave_profile)
    assert not report.semantic.passed
    assert not report.overall_passed
    assert "stream_count" in report.semantic.message
    assert "play_events" in report.semantic.message
    # Didactic hint names the table that actually owns the column
    assert "daily_artist_metrics" in report.semantic.message


def test_column_qualifier_missing_from_from_join_is_rejected(
    soundwave_connector, soundwave_profile
):
    """Every SELECT reference must correspond to a table/alias actually present in
    FROM/JOIN — here 'pe' is referenced but play_events is never joined."""
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT t.title, pe.event_id FROM tracks t;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.semantic.passed
    assert "pe" in report.semantic.message
    assert "FROM/JOIN" in report.semantic.message


def test_unqualified_nonexistent_column_is_rejected(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(sql="SELECT stream_count FROM play_events;")
    report = agent.verify(candidate, soundwave_profile)
    assert not report.semantic.passed
    assert "daily_artist_metrics" in report.semantic.message  # owning-table hint


def test_valid_aliased_join_passes_semantic(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    candidate = SqlCandidate(
        sql=(
            "SELECT a.name AS artist_name, SUM(dam.stream_count) AS total_streams "
            "FROM artists a "
            "JOIN daily_artist_metrics dam ON a.artist_id = dam.artist_id "
            "GROUP BY a.artist_id, a.name "
            "ORDER BY total_streams DESC;"
        )
    )
    report = agent.verify(candidate, soundwave_profile)
    assert report.semantic.passed, report.semantic.message
    assert report.overall_passed


def test_derived_table_and_correlated_subquery_pass_semantic(
    soundwave_connector, soundwave_profile
):
    agent = _agent(soundwave_connector)
    derived = SqlCandidate(
        sql=(
            "SELECT x.artist_id, x.plays FROM "
            "(SELECT artist_id, COUNT(*) AS plays FROM track_artists GROUP BY artist_id) x;"
        )
    )
    report = agent.verify(derived, soundwave_profile)
    assert report.semantic.passed, report.semantic.message

    correlated = SqlCandidate(
        sql=(
            "SELECT t.title, "
            "(SELECT COUNT(*) FROM play_events pe WHERE pe.track_id = t.track_id) AS plays "
            "FROM tracks t;"
        )
    )
    report = agent.verify(correlated, soundwave_profile)
    assert report.semantic.passed, report.semantic.message


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


# -- Temporal grounding (relative window vs hardcoded period) -------------------------
# The observed bug: "most played artists in the last 8 months" generated
# `WHERE YEAR(pe.played_at) = 2024` — valid syntax, valid schema, wrong answer.
# The sanity layer must reject relative-window questions whose SQL has no
# CURDATE()/NOW() anchor, with a didactic message the regeneration loop can use.

_LAST_8_MONTHS_INTENT = Intent(
    raw_query="Who are the most played artists in the last 8 months?",
    time_range="last 8 months",
)

_HARDCODED_YEAR_SQL = (
    "SELECT ta.artist_id, a.name, COUNT(pe.event_id) AS play_count "
    "FROM track_artists ta "
    "JOIN play_events pe ON ta.track_id = pe.track_id "
    "JOIN artists a ON ta.artist_id = a.artist_id "
    "WHERE YEAR(pe.played_at) = 2024 AND pe.event_type = 'play' "
    "GROUP BY ta.artist_id, a.name ORDER BY play_count DESC;"
)


def test_relative_window_with_hardcoded_year_fails_sanity(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    report = agent.verify(
        SqlCandidate(sql=_HARDCODED_YEAR_SQL), soundwave_profile, _LAST_8_MONTHS_INTENT
    )
    assert not report.sanity.passed
    assert not report.overall_passed
    assert "temporal mismatch" in report.sanity.message.lower()
    assert "last 8 months" in report.sanity.message.lower()

    # The mechanical repair rewrites the hardcoded year into a rolling window …
    assert report.repaired_sql is not None
    assert "DATE_SUB(CURDATE(), INTERVAL 8 MONTH)" in report.repaired_sql
    assert "2024" not in report.repaired_sql

    # … and the repaired SQL re-verifies clean (the orchestrator repair loop
    # relies on exactly this, same as the = NULL repair).
    repaired_report = agent.verify(
        SqlCandidate(sql=report.repaired_sql), soundwave_profile, _LAST_8_MONTHS_INTENT
    )
    assert repaired_report.overall_passed


def test_relative_window_with_curdate_anchor_passes(soundwave_connector, soundwave_profile):
    agent = _agent(soundwave_connector)
    sql = _HARDCODED_YEAR_SQL.replace(
        "YEAR(pe.played_at) = 2024",
        "pe.played_at >= DATE_SUB(CURDATE(), INTERVAL 8 MONTH)",
    )
    report = agent.verify(SqlCandidate(sql=sql), soundwave_profile, _LAST_8_MONTHS_INTENT)
    assert report.syntax.passed, report.syntax.message
    assert report.semantic.passed, report.semantic.message
    assert report.sanity.passed, report.sanity.message
    assert report.overall_passed


def test_explicit_year_question_allows_hardcoded_year(soundwave_connector, soundwave_profile):
    # "in 2024" is a fixed period the user named — a literal filter is correct.
    agent = _agent(soundwave_connector)
    intent = Intent(raw_query="Who were the most played artists in 2024?", time_range="in 2024")
    report = agent.verify(SqlCandidate(sql=_HARDCODED_YEAR_SQL), soundwave_profile, intent)
    assert report.sanity.passed
    assert report.overall_passed


def test_year_arithmetic_for_month_window_fails_unit_check(soundwave_connector, soundwave_profile):
    # The observed bug (2026-07-17): "most reproduced artists of the last 7 months"
    # generated `YEAR(pe.played_at) >= YEAR(CURDATE()) - 7` — anchored to CURDATE()
    # (so it passed the old anchor-only check) but a 7-YEAR calendar filter.
    agent = _agent(soundwave_connector)
    intent = Intent(
        raw_query="Who are the most reproduced artists of the last 7 months?",
        time_range="last 7 months",
    )
    sql = (
        "SELECT a.name, COUNT(*) AS play_count "
        "FROM play_events pe "
        "JOIN track_artists ta ON pe.track_id = ta.track_id "
        "JOIN artists a ON ta.artist_id = a.artist_id "
        "WHERE YEAR(pe.played_at) >= YEAR(CURDATE()) - 7 "
        "GROUP BY a.artist_id, a.name ORDER BY play_count DESC;"
    )
    report = agent.verify(SqlCandidate(sql=sql), soundwave_profile, intent)
    assert not report.sanity.passed
    assert not report.overall_passed
    assert "unit mismatch" in report.sanity.message.lower()
    assert "INTERVAL 7 MONTH" in report.sanity.message

    # The mechanical repair rewrites the YEAR() arithmetic into the strict window …
    assert report.repaired_sql is not None
    assert "DATE_SUB(CURDATE(), INTERVAL 7 MONTH)" in report.repaired_sql
    assert "YEAR(" not in report.repaired_sql

    # … and the repaired SQL re-verifies clean.
    repaired_report = agent.verify(SqlCandidate(sql=report.repaired_sql), soundwave_profile, intent)
    assert repaired_report.overall_passed, (
        repaired_report.syntax.message,
        repaired_report.semantic.message,
        repaired_report.sanity.message,
    )


def test_wrong_interval_unit_fails_unit_check(soundwave_connector, soundwave_profile):
    # INTERVAL 8 YEAR for "last 8 months" is anchored but the wrong unit.
    agent = _agent(soundwave_connector)
    sql = _HARDCODED_YEAR_SQL.replace(
        "YEAR(pe.played_at) = 2024",
        "pe.played_at >= DATE_SUB(CURDATE(), INTERVAL 8 YEAR)",
    )
    report = agent.verify(SqlCandidate(sql=sql), soundwave_profile, _LAST_8_MONTHS_INTENT)
    assert not report.sanity.passed
    assert "unit mismatch" in report.sanity.message.lower()


def test_weeks_window_accepts_exact_day_equivalent(soundwave_connector, soundwave_profile):
    # "past 2 weeks" may be written as INTERVAL 14 DAY (exact equivalence) —
    # the profile's own documented example.
    agent = _agent(soundwave_connector)
    intent = Intent(
        raw_query="Which tracks were played in the past 2 weeks?",
        time_range="past 2 weeks",
    )
    sql = (
        "SELECT t.title, COUNT(*) AS plays FROM play_events pe "
        "JOIN tracks t ON pe.track_id = t.track_id "
        "WHERE pe.played_at >= DATE_SUB(CURDATE(), INTERVAL 14 DAY) "
        "GROUP BY t.track_id, t.title ORDER BY plays DESC;"
    )
    report = agent.verify(SqlCandidate(sql=sql), soundwave_profile, intent)
    assert report.sanity.passed, report.sanity.message
    assert report.overall_passed


def test_no_intent_skips_temporal_check(soundwave_connector, soundwave_profile):
    # Backward compatibility: verify() without an intent runs the original checks only.
    agent = _agent(soundwave_connector)
    report = agent.verify(SqlCandidate(sql=_HARDCODED_YEAR_SQL), soundwave_profile)
    assert report.sanity.passed
    assert report.overall_passed


def test_history_segment_relative_phrase_does_not_refire(soundwave_connector, soundwave_profile):
    # A relative phrase in an injected [History] turn must not block the current
    # (time-free) question.
    agent = _agent(soundwave_connector)
    intent = Intent(
        raw_query=(
            "[History] Who were the most played artists in the last 8 months? "
            "[Current] And which of them are from Colombia?"
        )
    )
    sql = "SELECT name FROM artists WHERE country = 'CO';"
    report = agent.verify(SqlCandidate(sql=sql), soundwave_profile, intent)
    assert report.sanity.passed
    assert report.overall_passed
