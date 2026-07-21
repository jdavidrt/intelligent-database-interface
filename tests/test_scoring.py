"""Pins the EX comparison algorithm to EVALUATION_PROTOCOL.md §3.2 and §3.3.

Fully offline: hand-built row lists only, no database, no LLM, no backend.
`evaluation/scoring.py` is the one module whose bugs would corrupt every
published figure without ever raising, so it is tested in isolation and before
being wired into the run harness.

Each test names the rule it pins. §0.2 forbids changing the algorithm after the
first scored run, which makes these tests the enforcement mechanism.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from evaluation.scoring import (
    compare_against_any,
    compare_results,
    values_equal,
)

# -- §3.3 value normalization -------------------------------------------------


def test_null_equals_null() -> None:
    """§3.3: `NULL == NULL` is true for scoring purposes."""
    assert values_equal(None, None)


@pytest.mark.parametrize("other", [0, "", "null", 0.0, False])
def test_null_does_not_equal_anything_else(other: object) -> None:
    """A NULL against a value is a real difference in the answer, not a near-miss."""
    assert not values_equal(None, other)
    assert not values_equal(other, None)


def test_integers_compare_exactly() -> None:
    assert values_equal(48, 48)
    assert not values_equal(48, 47)


def test_money_rounds_to_two_decimals() -> None:
    """§3.3: decimal/money rounded to 2dp, then exact."""
    assert values_equal(Decimal("9.99"), 9.99)
    assert values_equal(9.99, 9.994)
    assert not values_equal(9.99, 10.01)


def test_float_sum_of_money_survives_representation_error() -> None:
    """A SUM over a DECIMAL column comes back as 4419.859999999999 from SQLite.

    It is still a two-decimal quantity, so the money rule applies and a
    candidate answering 4419.86 must pass. Getting this wrong would fail every
    revenue question in the corpus for a reason that is not the model's fault.
    """
    assert values_equal(4419.859999999999, 4419.86)


def test_money_rule_keys_on_ground_truth_not_on_the_candidate() -> None:
    """Which side decides that a value is money.

    Ground truth carries the column type; the candidate is whatever the model
    emitted. Requiring both sides to be two-decimal would silently make the
    rule stricter than §3.3 and fail an unrounded but correct answer.
    """
    assert values_equal(9.99, 9.994)  # money truth, unrounded candidate
    assert not values_equal(9.9942, 9.99)  # non-money truth: strict 1e-6


def test_average_is_not_treated_as_money() -> None:
    """The counterpart to the rule above, and the reason it is conditional.

    3.5852 (EC-05's mean track duration) is not a two-decimal quantity, so the
    strict 1e-6 float rule applies and a candidate answering 3.59 fails.
    Blanket 2dp rounding would have accepted a visibly different average.
    """
    assert not values_equal(3.5852, 3.59)


def test_float_relative_tolerance() -> None:
    """§3.3: floats compare at 1e-6 relative."""
    assert values_equal(0.123456789, 0.1234567891)
    assert not values_equal(0.123456789, 0.123556789)


def test_near_zero_uses_absolute_tolerance() -> None:
    """§3.3: if |G| < 1e-9, absolute tolerance 1e-9."""
    assert values_equal(0.0, 1e-10)
    assert not values_equal(0.0, 1e-6)


def test_strings_are_case_insensitive_and_trimmed() -> None:
    """§3.3: SoundWave collates utf8mb4_unicode_ci."""
    assert values_equal("The Weeknd", "  the weeknd ")
    assert not values_equal("The Weeknd", "The Weekend")


def test_date_equals_datetime_at_midnight() -> None:
    """§3.3: a DATE equals a DATETIME at midnight."""
    assert values_equal(date(2026, 6, 1), datetime(2026, 6, 1, 0, 0, 0))
    assert not values_equal(date(2026, 6, 1), datetime(2026, 6, 1, 12, 0, 0))


def test_dates_serialized_as_strings_still_compare_as_dates() -> None:
    """The candidate arrives over NDJSON with `default=str`.

    Ground truth is a native value from sqlite3; the candidate is the string
    the API serialized. Comparing those as strings would fail every temporal
    item in the corpus.
    """
    assert values_equal(datetime(2026, 6, 1, 0, 0, 0), "2026-06-01")
    assert values_equal(datetime(2026, 6, 1, 14, 30, 0), "2026-06-01 14:30:00")
    assert values_equal(Decimal("9.99"), "9.99")


def test_booleans_equal_zero_and_one() -> None:
    """§3.3: boolean / TINYINT(1) — 0/1 equal False/True."""
    assert values_equal(1, True)
    assert values_equal(0, False)
    assert not values_equal(1, False)


def test_units_are_not_coerced() -> None:
    """§3.3: units are not normalized — ms is not minutes.

    Silent unit coercion would hide exactly the semantic error class this
    project exists to catch.
    """
    assert not values_equal(215112, 3.5852)


# -- §3.2 result-set comparison -----------------------------------------------


def test_column_names_are_discarded() -> None:
    """§3.2.1: aliases are the model's free choice and carry no truth value."""
    truth = [{"artist_name": "Karol G"}]
    candidate = [{"whatever_i_called_it": "Karol G"}]
    assert compare_results(truth, candidate)


def test_extra_column_fails() -> None:
    """§3.2.2: the right answer plus an extra column did not answer the question."""
    truth = [("Karol G",)]
    candidate = [("Karol G", 12)]
    result = compare_results(truth, candidate)
    assert not result.matched
    assert "column count" in result.reason


def test_row_count_must_match() -> None:
    truth = [("a",), ("b",)]
    assert not compare_results(truth, [("a",)])
    assert not compare_results(truth, [("a",), ("b",), ("c",)])


def test_unordered_comparison_ignores_row_order() -> None:
    truth = [("b", 2), ("a", 1)]
    candidate = [("a", 1), ("b", 2)]
    assert compare_results(truth, candidate, order_matters=False)


def test_ordered_comparison_respects_row_order() -> None:
    """§3.2.3: order_matters => element-wise, no sorting.

    Set on items whose NL text implies an ordering, where returning the right
    rows in the wrong order is the wrong answer to "top 3".
    """
    truth = [("a", 1), ("b", 2)]
    candidate = [("b", 2), ("a", 1)]
    assert not compare_results(truth, candidate, order_matters=True)
    assert compare_results(truth, truth, order_matters=True)


def test_multiset_not_set_comparison() -> None:
    """§3.2.3: multiset comparison is deliberate — it catches a missing DISTINCT.

    Set comparison would score both of these as passes and let a spurious or
    absent DISTINCT through unnoticed.
    """
    truth = [("pop",), ("pop",), ("rock",)]
    assert not compare_results(truth, [("pop",), ("rock",)])  # missing duplicate
    assert not compare_results([("pop",), ("rock",)], truth)  # spurious duplicate


def test_nulls_sort_last_and_still_match() -> None:
    """Multiset sorting must be stable in the presence of NULLs (§3.2.3)."""
    truth = [(None, 1), ("a", 2)]
    candidate = [("a", 2), (None, 1)]
    assert compare_results(truth, candidate)


def test_tolerant_values_cannot_sort_into_different_positions() -> None:
    """The sort key rounds, so two values equal under §3.3 sort together.

    Without this the multiset comparison could pair row 0 against row 1 and
    report a mismatch between two result sets that are equal.
    """
    truth = [(1.0000000001,), (2.0,)]
    candidate = [(2.0,), (1.0,)]
    assert compare_results(truth, candidate)


def test_both_empty_matches() -> None:
    """§3.4 decides whether this is a pass; §3.2 only says the sets are equal.

    The distinction is load-bearing: a verification-blocked query also returns
    zero rows, and that is a fail (§3.4). scoring.py cannot see execution
    state, so it deliberately answers only the narrower question.
    """
    assert compare_results([], [])


def test_dict_rows_compare_positionally() -> None:
    """Rows arrive as dicts from the pipeline and tuples from the reference."""
    truth = [("Karol G", 5)]
    candidate = [{"name": "Karol G", "plays": 5}]
    assert compare_results(truth, candidate)


# -- §3.5 accepted_alternatives ----------------------------------------------


def test_accepted_alternative_matches() -> None:
    reference = [(3.5852,)]
    alternative = [(215112.0,)]
    result = compare_against_any([reference, alternative], [(215112.0,)])
    assert result.matched
    assert "accepted_alternative" in result.reason


def test_reference_match_is_reported_as_the_reference() -> None:
    reference = [(3.5852,)]
    alternative = [(215112.0,)]
    result = compare_against_any([reference, alternative], [(3.5852,)])
    assert result.matched
    assert "accepted_alternative" not in result.reason


def test_matching_neither_fails_with_the_reference_reason() -> None:
    result = compare_against_any([[(1,)], [(2,)]], [(3,)])
    assert not result.matched
    assert "1" in result.reason
