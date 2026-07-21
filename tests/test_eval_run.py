"""Pins the run harness's verdict rules to EVALUATION_PROTOCOL.md §3.4 and §3.6.

Offline: `score_item` is fed hand-built `QueryResult`/`AgentEvent` payloads of
the same shape POST /query streams, so no backend, LLM or database is involved.

The rule these tests exist for is §3.4's last two rows. A verification-blocked
query reports zero rows, exactly like a correct query whose ground truth is
empty — and the corpus contains genuinely-empty answers (§9 quirks 1 and 5).
Scoring the blocked case as a pass would be a false positive that flatters the
system precisely where it failed, and nothing in the result payload
distinguishes the two except `verify.overall_passed`.
"""

from __future__ import annotations

import pytest

from evaluation.corpus import CorpusItem
from evaluation.run import _verdict, score_item


def _item(**overrides) -> CorpusItem:
    base = {
        "id": "TEST-001",
        "corpus": "spider_style",
        "category": "Filtering / Segmentation",
        "difficulty": "easy",
        "nl": "how many standalone singles are there?",
        "reference_sql": "SELECT COUNT(*) FROM tracks WHERE album_id IS NULL",
        "order_matters": False,
        "expected_behaviour": "answer",
    }
    base.update(overrides)
    return CorpusItem(**base)


def _result(sql: str | None = "SELECT 1", rows=None, passed: bool = True, error=None) -> dict:
    verify = {
        "syntax": {"passed": passed, "message": "ok", "caveats": []},
        "semantic": {"passed": passed, "message": "ok", "caveats": []},
        "sanity": {"passed": passed, "message": "ok", "caveats": []},
        "overall_passed": passed,
    }
    return {
        "sql": {"sql": sql} if sql else None,
        "rows": rows if rows is not None else [],
        "row_count": len(rows or []),
        "verify": verify,
        "error": error,
    }


def _clarification_event() -> dict:
    return {
        "agent": "clarification",
        "status": "done",
        "payload": {"clarification_question": "Which metric do you mean?"},
    }


# -- §3.4 non-answers ---------------------------------------------------------


def test_blocked_query_with_empty_ground_truth_is_a_fail() -> None:
    """§3.4, the rule this whole module exists for.

    Ground truth is empty (the Adele case, §9 quirk 1) and the pipeline also
    reported zero rows — but because verification blocked the SQL, nothing
    executed. Comparing result sets alone would score this a pass.
    """
    scored = score_item(_item(), _result(passed=False, rows=[]), [], truths=[[]])
    assert scored["score"] == "fail"
    assert scored["edr_event"] is True
    assert "blocked" in scored["reason"]


def test_empty_result_that_actually_executed_is_a_pass() -> None:
    """§3.4: empty == empty is a pass *iff* the query really ran."""
    scored = score_item(_item(), _result(passed=True, rows=[]), [], truths=[[]])
    assert scored["score"] == "pass"
    assert scored["outcome"] == "answered"


def test_clarification_on_an_answer_item_is_a_fail() -> None:
    """§3.4: the pipeline ended in clarification but the item expects an answer."""
    result = _result(sql=None)
    scored = score_item(_item(), result, [_clarification_event()], truths=[[(8,)]])
    assert scored["score"] == "fail"
    assert scored["outcome"] == "clarified"


def test_pipeline_error_is_a_fail() -> None:
    result = _result(error="llama.cpp timed out")
    scored = score_item(_item(), result, [], truths=[[(8,)]])
    assert scored["score"] == "fail"
    assert scored["outcome"] == "pipeline_error"


def test_no_sql_generated_is_a_fail() -> None:
    scored = score_item(_item(), _result(sql=None), [], truths=[[(8,)]])
    assert scored["score"] == "fail"
    assert scored["outcome"] == "no_sql"


def test_meta_answer_on_a_data_question_is_a_fail() -> None:
    """The meta-question filter answering in prose is not an executed query."""
    events = [{"agent": "clarification", "status": "done", "payload": {"meta_answer": True}}]
    scored = score_item(_item(), _result(sql=None), events, truths=[[(8,)]])
    assert scored["score"] == "fail"
    assert scored["outcome"] == "meta_answer"


def test_correct_rows_pass() -> None:
    scored = score_item(_item(), _result(rows=[{"c": 8}]), [], truths=[[(8,)]])
    assert scored["score"] == "pass"


def test_wrong_rows_fail() -> None:
    scored = score_item(_item(), _result(rows=[{"c": 5}]), [], truths=[[(8,)]])
    assert scored["score"] == "fail"


def test_unexecutable_reference_sql_is_void_not_fail() -> None:
    """A corpus defect must not be charged to the model.

    §3.1 derives ground truth by execution; if that execution fails there is
    nothing to compare against, so the item leaves the EX denominator and is
    reported rather than silently counted as a failure.
    """
    scored = score_item(_item(), _result(rows=[{"c": 8}]), [], truths=None)
    assert scored["score"] == "void"


# -- §3.6 expected_behaviour --------------------------------------------------


def test_clarify_item_passes_only_when_the_pipeline_clarifies() -> None:
    item = _item(expected_behaviour="clarify", reference_sql=None)
    scored = score_item(item, _result(sql=None), [_clarification_event()], truths=None)
    assert scored["score"] == "pass"


def test_clarify_item_fails_when_the_pipeline_guesses() -> None:
    """§3.6: producing SQL is a fail even if that SQL is reasonable."""
    item = _item(expected_behaviour="clarify", reference_sql=None)
    scored = score_item(item, _result(rows=[{"c": 1}]), [], truths=None)
    assert scored["score"] == "fail"
    assert scored["outcome"] == "answered"


def test_block_item_passes_only_when_verification_blocks() -> None:
    item = _item(expected_behaviour="block", reference_sql=None)
    assert score_item(item, _result(passed=False), [], truths=None)["score"] == "pass"
    assert score_item(item, _result(passed=True), [], truths=None)["score"] == "fail"


def test_order_matters_is_honoured_by_the_scorer() -> None:
    item = _item(order_matters=True)
    truths = [[("a", 1), ("b", 2)]]
    ordered = _result(rows=[{"n": "a", "v": 1}, {"n": "b", "v": 2}])
    shuffled = _result(rows=[{"n": "b", "v": 2}, {"n": "a", "v": 1}])
    assert score_item(item, ordered, [], truths)["score"] == "pass"
    assert score_item(item, shuffled, [], truths)["score"] == "fail"


# -- §4.4 verdicts ------------------------------------------------------------


@pytest.mark.parametrize(
    "passed,caveats,expected",
    [
        (True, [], "pass"),
        (True, ["ambiguous bridge"], "caution"),
        (False, [], "fail"),
    ],
)
def test_verdict_mirrors_verify_report(passed: bool, caveats: list, expected: str) -> None:
    """A `caution` never blocks (§4.4), so it must not be pooled with `fail`."""
    verify = {
        "syntax": {"passed": True, "message": "", "caveats": []},
        "semantic": {"passed": passed, "message": "", "caveats": caveats},
        "sanity": {"passed": True, "message": "", "caveats": []},
        "overall_passed": passed,
    }
    assert _verdict(verify) == expected


def test_caution_still_scores_on_its_rows() -> None:
    """The load-bearing invariant: a caveat never blocks execution.

    A `caution` query ran, so it is scored by result comparison like any other
    answer — not penalised for carrying a caveat.
    """
    result = _result(rows=[{"c": 8}])
    result["verify"]["semantic"]["caveats"] = ["playlists->tracks bridge is ambiguous"]
    scored = score_item(_item(), result, [], truths=[[(8,)]])
    assert scored["score"] == "pass"
    assert _verdict(result["verify"]) == "caution"
