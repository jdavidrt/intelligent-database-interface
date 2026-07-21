"""Failure interpretation for a scored run — the "so what" layer of a report.

A report already lists every item's verdict and reason. That answers *what*
failed and is nearly useless at 225 items: the reader has to notice by hand that
three separate blocked queries are one root cause wearing three faces. This
module does that grouping mechanically — a failure taxonomy, and recurring
message signatures with the identifiers normalized away.

It reads the scored records and nothing else. It never re-scores, never changes
a verdict, and has no access to thresholds. That separation is the point: under
EVALUATION_PROTOCOL.md §0.2 the instrument may be fixed but the target may not
move, and a diagnostics layer that could reach back into scoring would be
exactly the mechanism for moving it.

The §0.2 cost of *reading* this section is stated in `DISCIPLINE_NOTE` and is
rendered into every report, because it is easy to forget: once a defect found
here is fixed, these corpora have served as a development set for that fix.
"""

from __future__ import annotations

import re
from typing import Any

# Rendered verbatim into the Markdown report, directly above the interpretation.
DISCIPLINE_NOTE = (
    "**§0.2 — instrument, not target.** This section interprets the run; it does not "
    "re-score it. Nothing below may justify changing a threshold, a corpus item, a "
    "tolerance or the EX comparison algorithm — those are frozen. A defect found here is "
    "fixed in the *system* (prompt, schema summary, verifier, training data), never in the "
    "measurement, and the fix is logged in §11.\n>\n> Note what reading this costs. Once a "
    "failure below drives a change, these corpora have acted as a **development set** for "
    "that change, and every later EX on them is optimistic to that extent. That is a "
    "legitimate use — it is what a diagnostic corpus is for — but §4.2 must say so rather "
    "than report the later figure as an independent result."
)

# -- failure taxonomy ----------------------------------------------------------
#
# Keyed by the (outcome, reason-shape) pair the scorer already produces. The
# reason prefixes come from evaluation/scoring.py::compare_results and are
# matched, not re-derived, so this stays honest if that module changes wording:
# an unrecognised reason falls through to `wrong_answer_other` rather than being
# silently binned as something it is not.
FAILURE_LABELS: dict[str, str] = {
    "blocked": "verification blocked the SQL before execution (an EDR event, §4)",
    "wrong_row_count": "executed, but returned a different number of rows",
    "wrong_column_count": "executed, but returned a different number of columns",
    "wrong_values": "executed with the right shape, but at least one value differs",
    "wrong_answer_other": "executed and did not match, reason unclassified",
    "clarified": "ended in a clarification question where an answer was expected (§3.4)",
    "did_not_clarify": "produced SQL where §3.6 required a clarification",
    "not_blocked": "executed where §3.6 required a refusal",
    "no_sql": "no SQL was generated",
    "meta_answer": "answered in prose as a meta question instead of querying",
    "pipeline_error": "pipeline error or timeout",
}


def classify_failure(record: dict[str, Any]) -> str:
    """One failure class for a failed record. Pure function of what was scored."""
    outcome = record.get("outcome") or ""
    reason = record.get("reason") or ""
    expected = record.get("expected_behaviour", "answer")

    if outcome == "blocked":
        return "blocked"
    if outcome == "clarified":
        return "clarified"
    if outcome in ("no_sql", "meta_answer", "pipeline_error"):
        return outcome
    if outcome == "answered":
        if expected == "clarify":
            return "did_not_clarify"
        if expected == "block":
            return "not_blocked"
        if reason.startswith("row count "):
            return "wrong_row_count"
        if "column count " in reason:
            return "wrong_column_count"
        if " col " in reason:
            return "wrong_values"
    return "wrong_answer_other"


# -- message signatures --------------------------------------------------------
#
# Two failures are "the same" when their messages differ only in which table,
# column or number they name. Normalizing those away is what turns three blocked
# items into one finding.
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"|`[^`]*`")
_QUALIFIED = re.compile(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*\b")
# The colon is required. Without it this also matched the scorer's own
# "column count 2 != expected 3", normalizing the word "count" into an
# identifier and inventing a signature nobody wrote.
_AFTER_KEYWORD = re.compile(r"\b(column|table|alias|relation)(\s*:\s+)([A-Za-z_]\w*)", re.I)
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


def signature(message: str) -> str:
    """Collapse a failure message to its shape.

    Only the first clause is kept: engine errors append a increasingly specific
    tail ("...does not exist in table 'x'" vs "...in any table present in FROM")
    which splits one root cause into several signatures.
    """
    text = (message or "").split(";")[0].strip()
    text = _QUOTED.sub("<id>", text)
    text = _QUALIFIED.sub("<id>", text)
    text = _AFTER_KEYWORD.sub(lambda m: f"{m.group(1)}{m.group(2)}<id>", text)
    text = _NUMBER.sub("<n>", text)
    return text[:160]


def _counted(pairs: list[tuple[str, str]], minimum: int = 1) -> list[dict[str, Any]]:
    """Group (signature, item_id) pairs, most frequent first."""
    grouped: dict[str, list[str]] = {}
    for sig, item_id in pairs:
        grouped.setdefault(sig, []).append(item_id)
    rows = [
        {"signature": sig, "count": len(ids), "items": ids}
        for sig, ids in grouped.items()
        if len(ids) >= minimum
    ]
    rows.sort(key=lambda row: (-row["count"], row["signature"]))
    return rows


# -- the report ----------------------------------------------------------------


def diagnose(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Group a run's failures into classes and recurring signatures."""
    failures = [r for r in records if r.get("score") == "fail"]

    taxonomy: dict[str, dict[str, Any]] = {}
    for record in failures:
        klass = classify_failure(record)
        bucket = taxonomy.setdefault(
            klass, {"count": 0, "label": FAILURE_LABELS.get(klass, klass), "items": []}
        )
        bucket["count"] += 1
        bucket["items"].append(record["id"])
    ordered = dict(sorted(taxonomy.items(), key=lambda kv: -kv[1]["count"]))

    blocked = [
        (signature(r.get("reason", "")), r["id"])
        for r in failures
        if classify_failure(r) == "blocked"
    ]
    wrong = [
        (signature(r.get("reason", "")), r["id"])
        for r in failures
        if classify_failure(r).startswith("wrong_")
    ]
    # Caveats on queries that *passed*: §4.4's soft-FPR signal. A caution never
    # blocks, so these are usability findings, not correctness failures — but a
    # caveat on nearly every answer trains the user to ignore caveats.
    caveats = [
        (signature(caveat), r["id"])
        for r in records
        if r.get("score") == "pass"
        for caveat in (r.get("caveats") or [])
    ]

    scored = [r for r in records if r.get("score") in ("pass", "fail")]
    return {
        "discipline": DISCIPLINE_NOTE,
        "scored": len(scored),
        "failed": len(failures),
        "taxonomy": ordered,
        "blocked_signatures": _counted(blocked),
        "wrong_answer_signatures": _counted(wrong),
        "caveat_signatures_on_passing_items": _counted(caveats),
        "recurring": _counted(blocked + wrong, minimum=2),
    }
