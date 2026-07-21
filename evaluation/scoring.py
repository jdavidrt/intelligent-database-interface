"""Execution Accuracy comparison — EVALUATION_PROTOCOL.md §3.2 and §3.3, in code.

This module is deliberately free of any I/O, any LLM and any database: it takes
two lists of rows and says whether they match. That makes the one piece of the
harness whose bugs would silently corrupt every reported figure testable
offline, in isolation, against hand-built row lists (`tests/test_scoring.py`).

Two implementation decisions are worth stating up front, because neither is
spelled out by the protocol and both change results:

1. **Types are recovered, not trusted.** Ground truth comes from sqlite3 as
   native Python values; the candidate arrives over NDJSON serialized with
   `default=str`, so a date is `"2026-06-01"` and a decimal may be `"9.99"`.
   Comparing those under §3.3's *String* rule would fail every money and date
   comparison in the corpus for reasons that have nothing to do with the model.
   `_coerce` therefore reads a value's *shape* (null / number / date / string)
   rather than its Python type, and the §3.3 rule is chosen from the shape both
   sides share.

2. **"Money to 2dp" needs a discriminator the data does not carry.** SQLite
   returns DECIMAL columns as plain floats, so nothing in the value says
   "money". The rule here is: apply the 2-decimal rule when the *ground truth*
   is already a two-decimal quantity (up to float representation error), and
   fall back to the strict 1e-6 relative tolerance otherwise. Ground truth is
   where the column type lives, so it is the side that decides. A price of 9.99
   and a summed total of 4419.859999999999 are two-decimal quantities and get
   the money rule — an unrounded candidate of 9.994 passes, as §3.3 requires.
   An average duration of 3.5852 is not, so a candidate answering 3.59 fails;
   blanket 2dp rounding would have quietly accepted a wrong average.

§3.3's "units are not normalized" is honoured by omission: nothing here
converts ms to minutes or cents to currency. That is the point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

# §3.3 tolerances. Frozen — see §0.2.
FLOAT_RELATIVE_TOLERANCE = 1e-6
FLOAT_ABSOLUTE_TOLERANCE = 1e-9
NEAR_ZERO = 1e-9
MONEY_DECIMAL_PLACES = 2

Row = Sequence[Any]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")


@dataclass(frozen=True)
class Comparison:
    """Outcome of comparing a candidate result set against one ground truth."""

    matched: bool
    reason: str = ""

    def __bool__(self) -> bool:  # lets callers write `if compare(...)`
        return self.matched


# -- value shapes -------------------------------------------------------------


def _coerce(value: Any) -> tuple[str, Any]:
    """Classify a value into ("null"|"num"|"date"|"str", canonical form).

    Strings are probed for a date/datetime and then for a number, so that a
    JSON-serialized `"2026-06-01"` or `"9.99"` compares as what it is. A string
    that is genuinely textual and happens to look numeric (a track titled
    "1979") is coerced identically on both sides, so the comparison is still
    correct — it merely runs through the numeric rule.
    """
    if value is None:
        return ("null", None)

    # bool before int: `isinstance(True, int)` is True in Python, and §3.3 wants
    # 0/1 to equal False/True anyway, so both land on the numeric rule.
    if isinstance(value, bool):
        return ("num", 1.0 if value else 0.0)

    if isinstance(value, (int, float, Decimal)):
        return ("num", float(value))

    if isinstance(value, datetime):
        return ("date", value)
    if isinstance(value, date):
        return ("date", datetime(value.year, value.month, value.day))

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ("str", "")
        if _DATE_RE.match(text) or _DATETIME_RE.match(text):
            try:
                return ("date", datetime.fromisoformat(text.replace(" ", "T")))
            except ValueError:
                pass
        try:
            return ("num", float(text))
        except ValueError:
            return ("str", text.casefold())

    if isinstance(value, (bytes, bytearray)):
        return ("str", value.decode("utf-8", "replace").strip().casefold())

    return ("str", str(value).strip().casefold())


def _is_two_decimal(x: float) -> bool:
    """True when x is a 2-decimal quantity up to float representation error.

    4419.859999999999 (a SUM over a DECIMAL column) is; 3.5852 (a mean) is not.
    See the module docstring for why this stands in for "is this money?".
    """
    return abs(x - round(x, MONEY_DECIMAL_PLACES)) <= max(NEAR_ZERO, abs(x) * 1e-12)


def values_equal(truth: Any, candidate: Any) -> bool:
    """Single-value comparison per §3.3."""
    truth_kind, truth_value = _coerce(truth)
    candidate_kind, candidate_value = _coerce(candidate)

    # §3.3: NULL == NULL is true for scoring purposes. A NULL against anything
    # else is not — that is a real difference in the answer.
    if truth_kind == "null" or candidate_kind == "null":
        return truth_kind == candidate_kind

    if truth_kind != candidate_kind:
        return False

    if truth_kind == "str":
        return truth_value == candidate_value

    if truth_kind == "date":
        # A DATE equals a DATETIME at midnight, which comparing the parsed
        # datetimes gives for free (date-only parses to 00:00:00).
        return truth_value == candidate_value

    # numeric
    if float(truth_value).is_integer() and float(candidate_value).is_integer():
        return truth_value == candidate_value
    # Near-zero first: §3.3 makes the absolute tolerance unconditional for
    # |G| < 1e-9, and 0.0 is trivially a "two-decimal quantity", so letting the
    # money rule run first would accept anything that rounds to 0.00.
    if abs(truth_value) < NEAR_ZERO:
        return abs(candidate_value - truth_value) <= FLOAT_ABSOLUTE_TOLERANCE
    # The money rule keys on the *ground truth* only, because that is where the
    # column type lives: §3.3 says "decimal/money -> round to 2dp, then exact",
    # so an unrounded candidate (9.994 against a price of 9.99) must pass.
    # Requiring both sides to be two-decimal would have silently converted that
    # rule into something stricter than the protocol.
    if _is_two_decimal(truth_value):
        return round(truth_value, MONEY_DECIMAL_PLACES) == round(
            candidate_value, MONEY_DECIMAL_PLACES
        )
    return abs(candidate_value - truth_value) <= abs(truth_value) * FLOAT_RELATIVE_TOLERANCE


# -- row and result-set comparison --------------------------------------------


def _sort_key(row: Row) -> tuple:
    """Canonical key for multiset comparison (§3.2.3), NULLs last.

    Numbers are rounded into the key so that two values that compare equal
    under §3.3's tolerance cannot sort into different positions. The tolerant
    comparison still runs element-wise afterwards; this only fixes the order.
    """
    key: list[tuple] = []
    for value in row:
        kind, coerced = _coerce(value)
        if kind == "null":
            key.append((3, ""))  # NULLs last
        elif kind == "num":
            key.append((0, f"{round(coerced, 6):.6f}"))
        elif kind == "date":
            key.append((1, coerced.isoformat()))
        else:
            key.append((2, coerced))
    return tuple(key)


def as_rows(rows: Iterable[Any]) -> list[tuple]:
    """Normalize a result set to a list of positional tuples.

    Accepts what the pipeline returns (list of dicts, column order preserved by
    sqlite3.Row -> dict) and what `evaluation.corpus.execute` returns (tuples).
    §3.2.1 discards column names, so only the ordering of a dict's values is
    ever read — never its keys.
    """
    out: list[tuple] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(tuple(row.values()))
        elif isinstance(row, (list, tuple)):
            out.append(tuple(row))
        else:  # a bare scalar row
            out.append((row,))
    return out


def compare_results(
    truth: Iterable[Any],
    candidate: Iterable[Any],
    *,
    order_matters: bool = False,
) -> Comparison:
    """Compare two result sets per §3.2. Returns a Comparison with a reason."""
    truth_rows = as_rows(truth)
    candidate_rows = as_rows(candidate)

    # §3.2.4 — row count must match. Checked first because it gives the most
    # useful failure message; §3.2 derives it from the row comparison anyway.
    if len(truth_rows) != len(candidate_rows):
        return Comparison(
            False,
            f"row count {len(candidate_rows)} != expected {len(truth_rows)}",
        )

    if not truth_rows:
        # Both empty. §3.4 decides whether an empty answer is a pass; that
        # depends on whether the query executed, which this module cannot see.
        return Comparison(True, "both result sets empty")

    # §3.2.2 — column count must match. A right answer plus three extra columns
    # did not answer the question asked.
    truth_width = len(truth_rows[0])
    candidate_width = len(candidate_rows[0])
    if truth_width != candidate_width:
        return Comparison(
            False,
            f"column count {candidate_width} != expected {truth_width}",
        )

    if not order_matters:
        truth_rows = sorted(truth_rows, key=_sort_key)
        candidate_rows = sorted(candidate_rows, key=_sort_key)

    for index, (truth_row, candidate_row) in enumerate(zip(truth_rows, candidate_rows)):
        if len(truth_row) != len(candidate_row):
            return Comparison(
                False,
                f"row {index}: column count {len(candidate_row)} != expected {len(truth_row)}",
            )
        for column, (truth_value, candidate_value) in enumerate(zip(truth_row, candidate_row)):
            if not values_equal(truth_value, candidate_value):
                where = "row" if order_matters else "sorted row"
                return Comparison(
                    False,
                    f"{where} {index} col {column}: {candidate_value!r} != {truth_value!r}",
                )

    return Comparison(True, f"{len(truth_rows)} row(s) matched")


def compare_against_any(
    truths: Sequence[Iterable[Any]],
    candidate: Iterable[Any],
    *,
    order_matters: bool = False,
) -> Comparison:
    """§3.5 — pass if the candidate matches the reference or any alternative.

    `truths[0]` is the reference; the rest are `accepted_alternatives`, which
    §0.2 requires to have been authored with the corpus, never after a run.
    """
    first: Comparison | None = None
    for position, truth in enumerate(truths):
        result = compare_results(truth, candidate, order_matters=order_matters)
        if result.matched:
            if position == 0:
                return result
            return Comparison(True, f"matched accepted_alternative #{position}: {result.reason}")
        if first is None:
            first = result
    # `first is None`, never `first or ...`: Comparison.__bool__ reports the
    # verdict, so a legitimate failed comparison is falsy and `or` would throw
    # away its reason.
    return Comparison(False, "no ground truth to compare against") if first is None else first
