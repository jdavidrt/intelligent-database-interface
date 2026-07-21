"""Pins the failure-interpretation layer of a scored run.

Offline — `diagnose` reads scored records and nothing else, so these tests feed
it hand-built records of the shape `run_sweep` produces.

Two things are being protected. First, the taxonomy must key off the *reason
strings evaluation/scoring.py actually emits*; if that module rewords a message
the classifier must degrade to `wrong_answer_other` rather than silently bin a
failure as something it is not. Second, signature normalization must collapse
exactly the noise (identifiers, literals) and nothing else — over-normalizing
merges unrelated findings into one confident-looking row, which is worse than
not grouping at all.
"""

from __future__ import annotations

import pytest

from evaluation.diagnostics import (
    DISCIPLINE_NOTE,
    FAILURE_LABELS,
    classify_failure,
    diagnose,
    signature,
)


def _record(**overrides) -> dict:
    base = {
        "id": "SPIDER-001",
        "score": "fail",
        "outcome": "answered",
        "reason": "row count 12 != expected 40",
        "expected_behaviour": "answer",
        "caveats": [],
    }
    base.update(overrides)
    return base


# -- taxonomy -----------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome,reason,expected",
    [
        ("blocked", "verification blocked the SQL — no such column: x", "blocked"),
        ("answered", "row count 12 != expected 40", "wrong_row_count"),
        ("answered", "column count 2 != expected 3", "wrong_column_count"),
        ("answered", "sorted row 0 col 1: 12 != 40", "wrong_values"),
        ("answered", "row 3 col 0: 'a' != 'b'", "wrong_values"),
        ("clarified", "ended in clarification (§3.4)", "clarified"),
        ("no_sql", "no SQL generated", "no_sql"),
        ("meta_answer", "answered as a meta question", "meta_answer"),
        ("pipeline_error", "pipeline error: timeout", "pipeline_error"),
    ],
)
def test_classify_failure(outcome: str, reason: str, expected: str) -> None:
    assert classify_failure(_record(outcome=outcome, reason=reason)) == expected


def test_unrecognised_reason_degrades_rather_than_mislabels() -> None:
    """If scoring.py rewords a message, the classifier must not guess.

    `wrong_answer_other` is a visible 'I don't know' in the report; a confident
    wrong bin would send someone chasing the wrong root cause.
    """
    record = _record(reason="the comparison went sideways in a novel way")
    assert classify_failure(record) == "wrong_answer_other"


def test_expected_behaviour_changes_the_class_of_the_same_outcome() -> None:
    """Producing SQL is a success for an `answer` item and a failure for a
    `clarify` one (§3.6) — the class must say which."""
    answered = {"outcome": "answered", "reason": "sorted row 0 col 0: 1 != 2"}
    assert classify_failure(_record(**answered, expected_behaviour="clarify")) == "did_not_clarify"
    assert classify_failure(_record(**answered, expected_behaviour="block")) == "not_blocked"


def test_every_class_has_a_human_label() -> None:
    """The report prints `label`; a missing one would render a bare slug."""
    reasons = [
        ("blocked", "blocked"),
        ("answered", "row count 1 != expected 2"),
        ("answered", "column count 1 != expected 2"),
        ("answered", "sorted row 0 col 0: 1 != 2"),
        ("answered", "unclassifiable"),
        ("clarified", "x"),
        ("no_sql", "x"),
        ("meta_answer", "x"),
        ("pipeline_error", "x"),
    ]
    produced = {classify_failure(_record(outcome=o, reason=r)) for o, r in reasons}
    produced |= {"did_not_clarify", "not_blocked"}
    assert produced <= set(FAILURE_LABELS)


# -- signatures ---------------------------------------------------------------


def test_identifiers_and_literals_are_normalized_away() -> None:
    assert signature("row count 12 != expected 40") == "row count <n> != expected <n>"
    assert signature("sorted row 0 col 1: 12 != 40") == "sorted row <n> col <n>: <n> != <n>"


def test_the_three_column_resolution_failures_collapse_to_one_signature() -> None:
    """The finding this module exists to surface.

    Three blocked items in the 2026-07-21 pilot were one root cause — column
    resolution — reported as a qualified name, a bare name and a name on the
    wrong table. Read item by item they look like three problems.
    """
    messages = [
        "verification blocked the SQL — Engine EXPLAIN rejected the query: no such column: "
        "s.has_downloads; Column 'has_downloads' does not exist in table 'subscription_plans'",
        "verification blocked the SQL — Engine EXPLAIN rejected the query: no such column: "
        "explicit; Column 'explicit' does not exist in any table present in FROM",
        "verification blocked the SQL — Engine EXPLAIN rejected the query: no such column: "
        "user_follows_artists.referred_by_user_id; Column does not exist",
    ]
    assert len({signature(m) for m in messages}) == 1


def test_column_count_is_not_mistaken_for_an_identifier() -> None:
    """Regression: the keyword rule once matched 'column count' and normalized
    the word `count`, inventing the signature `column <id> <n> != expected <n>`."""
    assert signature("column count 2 != expected 3") == "column count <n> != expected <n>"


def test_distinct_root_causes_stay_distinct() -> None:
    """Over-normalizing is the failure mode that matters: it merges unrelated
    findings into one row that looks like a confident conclusion."""
    assert signature("no such column: x") != signature("no such table: x")
    assert signature("row count 1 != expected 2") != signature("column count 1 != expected 2")


# -- the assembled report -----------------------------------------------------


def test_diagnose_groups_and_ranks() -> None:
    records = [
        _record(id="A", outcome="blocked", reason="blocked: no such column: a.b"),
        _record(id="B", outcome="blocked", reason="blocked: no such column: c"),
        _record(id="C", reason="row count 1 != expected 2"),
        _record(id="D", score="pass", outcome="answered", reason="2 row(s) matched"),
    ]
    report = diagnose(records)

    assert report["scored"] == 4 and report["failed"] == 3
    assert report["taxonomy"]["blocked"]["count"] == 2
    assert report["taxonomy"]["blocked"]["items"] == ["A", "B"]
    # Only signatures seen more than once are "recurring"; the singleton row
    # count failure must not be promoted into a finding.
    assert [row["count"] for row in report["recurring"]] == [2]
    assert report["recurring"][0]["items"] == ["A", "B"]


def test_caveats_are_collected_from_passing_items_only() -> None:
    """§4.4's soft signal is about legal SQL. A caveat on a failed query is not
    a false positive — the query was wrong anyway."""
    records = [
        _record(id="P", score="pass", caveats=["ambiguous bridge playlists->tracks"]),
        _record(id="F", score="fail", caveats=["ambiguous bridge playlists->tracks"]),
    ]
    soft = diagnose(records)["caveat_signatures_on_passing_items"]
    assert len(soft) == 1
    assert soft[0]["items"] == ["P"]


def test_a_clean_run_reports_no_failures() -> None:
    report = diagnose([_record(id="A", score="pass"), _record(id="B", score="pass")])
    assert report["failed"] == 0
    assert report["taxonomy"] == {}
    assert report["recurring"] == []


def test_void_items_are_outside_the_scored_denominator() -> None:
    """A corpus defect is not a model failure (§3.1) and must not dilute the
    failure rate the diagnostics quote."""
    report = diagnose([_record(id="A", score="void"), _record(id="B", score="fail")])
    assert report["scored"] == 1
    assert report["failed"] == 1


def test_discipline_note_states_the_dev_set_cost() -> None:
    """The §0.2 coherence requirement: the report must say out loud that acting
    on these findings turns the corpora into a development set."""
    assert "§0.2" in DISCIPLINE_NOTE
    assert "development set" in DISCIPLINE_NOTE
    assert "§4.2" in DISCIPLINE_NOTE
    assert diagnose([_record()])["discipline"] == DISCIPLINE_NOTE
