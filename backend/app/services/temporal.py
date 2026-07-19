"""Temporal — shared relative-time-window parsing and strict-predicate rules.

One source of truth for how a natural-language window ("last 7 months") maps to
SQL. Used from both sides of the pipeline so generation and verification can
never drift apart:

- SQLGenerator injects `strict_predicate_hint()` into the prompt, telling the
  model the exact DATE_SUB(...) predicate the window requires.
- VerificationAgent's sanity layer calls `unit_mismatch()` to reject SQL whose
  date filter uses the wrong number or unit — the observed failure was
  "last 7 months" answered with `YEAR(col) >= YEAR(CURDATE()) - 7`, a 7-YEAR
  window that still contained a CURDATE() anchor and so passed the old
  anchor-only check.

Strictness rule: the SQL's INTERVAL must carry the question's own number and
unit. The only accepted equivalences are exact ones — N weeks == 7N days,
N years == 12N months. Months are never convertible to days (28/29/30/31
ambiguity) and never expressible via YEAR() arithmetic.
"""

from __future__ import annotations

import re

NUMBER_WORD = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"twenty|thirty|sixty|ninety)"
)

# Any relative window at all (sized or not) — the anchor-required trigger.
RELATIVE_WINDOW_RE = re.compile(
    rf"\b(?:last|past|previous)\s+{NUMBER_WORD}\s+(?:day|week|month|year)s?\b"
    r"|\b(?:last|past|previous|this|current)\s+(?:day|week|month|year|quarter)\b"
    r"|\b(?:yesterday|today)\b",
    re.IGNORECASE,
)

# "last 8 months" / "past two weeks" — captures (number, unit) for strict checks.
WINDOW_SIZE_RE = re.compile(
    rf"\b(?:last|past|previous)\s+({NUMBER_WORD})\s+(day|week|month|year)s?\b",
    re.IGNORECASE,
)
SINGULAR_WINDOW_RE = re.compile(
    r"\b(?:last|past|previous)\s+(day|week|month|year)\b", re.IGNORECASE
)

WORD_TO_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "twenty": 20,
    "thirty": 30,
    "sixty": 60,
    "ninety": 90,
}


def extract_relative_window(question: str) -> tuple[int, str] | None:
    """'last 8 months' -> (8, 'month'); 'past week' -> (1, 'week'); None if the
    question names no sized relative window ('this year' has no fixed size)."""
    if not question:
        return None
    m = WINDOW_SIZE_RE.search(question)
    if m:
        raw_n = m.group(1).lower()
        n = int(raw_n) if raw_n.isdigit() else WORD_TO_NUM.get(raw_n)
        return (n, m.group(2).lower()) if n else None
    m = SINGULAR_WINDOW_RE.search(question)
    if m:
        return 1, m.group(1).lower()
    return None


def required_predicate(n: int, unit: str, column: str = "<date_column>") -> str:
    """The canonical strict predicate for a sized window."""
    return f"{column} >= DATE_SUB(CURDATE(), INTERVAL {n} {unit.upper()})"


def _accepted_intervals(n: int, unit: str) -> list[tuple[int, str]]:
    """Exactly-equivalent (number, unit) spellings for a window. Months have no
    day-count equivalent — INTERVAL {n} MONTH is the only accepted form."""
    unit = unit.lower()
    accepted = [(n, unit)]
    if unit == "week":
        accepted.append((7 * n, "day"))
    elif unit == "year":
        accepted.append((12 * n, "month"))
    return accepted


def unit_mismatch(sql: str, n: int, unit: str) -> str | None:
    """None when the SQL contains an INTERVAL carrying the window's exact number
    and unit (or an exact equivalent); otherwise a didactic failure message.

    `YEAR(col) >= YEAR(CURDATE()) - 7` for "last 7 months" fails here: it has a
    CURDATE() anchor but expresses a 7-year calendar filter, not a 7-month
    rolling window.
    """
    for acc_n, acc_unit in _accepted_intervals(n, unit):
        if re.search(rf"\bINTERVAL\s+'?{acc_n}'?\s+{acc_unit}s?\b", sql, re.IGNORECASE):
            return None
    return (
        f"Temporal unit mismatch: the question asks for a window of "
        f"{n} {unit}(s), but the SQL's date filter does not use "
        f"INTERVAL {n} {unit.upper()}. The filter must be exactly "
        f"{required_predicate(n, unit)} — same number, same unit. "
        f"YEAR() arithmetic (e.g. YEAR(col) >= YEAR(CURDATE()) - {n}) or a "
        f"different unit does not answer a {n}-{unit} window."
    )
