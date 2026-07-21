"""Read-only guard — one definition, shared by the verifier and every connector.

The same rule was written twice, as `sql.strip().upper().startswith("SELECT")`
in `VerificationAgent._layer_sanity` and again in `FileConnector.execute_read`.
Two copies of a safety rule drift, and these did — in both directions at once:

- **Too strict:** a CTE query starts with `WITH`, so every `WITH ... SELECT`
  was rejected as a non-SELECT statement despite being read-only. That blocks
  the natural idiom for rank-then-filter and top-N-per-group questions.
- **Too lax:** `SELECT 1; DROP TABLE users` starts with "SELECT", so the string
  check waved it through. SQLite's driver happens to refuse multiple statements
  on `execute()`, but that is the driver's accident, not this guard's doing, and
  MySQL on Day 4 does not offer the same protection.

Parsing decides both correctly: a CTE-headed query is an `exp.Select`, a
stacked statement is an `exp.Block`, and set operations (UNION/EXCEPT/INTERSECT)
are read-only `exp.SetOperation`s. Unparseable SQL fails closed.

Same rationale as `services/temporal.py`: a rule enforced in two places must
live in one module, or generation, verification and execution will disagree
about what they are enforcing.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

# Statement types that read and cannot write.
_READ_ONLY_TYPES = (exp.Select, exp.SetOperation)


def is_read_only(sql: str, dialect: str = "mysql") -> bool:
    """True when `sql` is a single read-only statement.

    Fails closed: anything that does not parse, or parses to more than one
    statement, is rejected. Callers raise or reject with their own message.
    """
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return False
    return isinstance(tree, _READ_ONLY_TYPES)
