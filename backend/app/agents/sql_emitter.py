"""Structured SQL emission — SQL_HARDENING_PLAN Step 2. **PARKED 2026-07-21.**

PARKED — NOT WIRED INTO THE PIPELINE
------------------------------------
Nothing imports this module. It was unwired from `sql_generator.py` when the
2026-07-21 13:21 run regressed EX from 53.8% to 34.5% against the same corpora
(`data/benchmarks/eval_2026-07-21_1321.{json,md}`), and the tree was reverted to
the 53.8% system.

Two mechanical causes were identified in that run, both traceable here:

- **Tripled string literals** — `WHERE albums.album_type = '''album'''` returned
  zero rows. `_quote()` below re-quotes a literal the plan had already quoted.
  Four failures (SPIDER-003, BIRD-001, SW-Q01, SW-Q04).
- **Spurious JOINs on single-table queries** — `SELECT COUNT(*) FROM tracks`
  became a join through `track_artists`, whose fan-out counts 49 tracks instead
  of 48. Five failures (SPIDER-002, BIRD-003, EXEC-002/004/006). Note this is
  the *inverse* of the defect the module was written to fix, described below.

The idea is sound and the diagnosis that motivated it still holds, so the module
is kept rather than deleted. `tests/test_sql_emitter.py` skips itself while this
module is unreachable and starts running again automatically the moment anything
under `backend/app` imports it — so reviving this is a one-line wiring change,
not a checklist. Fix `_quote` and the plan-scoped join logic before doing so.

The original rationale follows.

The planning step already proves the idea: llama.cpp compiles a JSON Schema
(enums included) into a GBNF grammar, so the sampler is *physically unable* to
emit an identifier outside the schema's vocabulary. Until now that guarantee
stopped at the plan. The final SQL was free-form prose with the statement
regexed out of it, and the 2026-07-21 pilot showed what that costs: the planner
correctly answered "Which subscription plans allow offline downloads?" with
`{"tables": ["subscription_plans"], "join_on": []}`, and the emitter went on to
invent a JOIN to `subscriptions` and read `s.has_downloads` off it. Half the
scored failures were the emitter overriding a plan that was already right.

This module closes that gap: the model fills in a *query object* whose every
identifier slot is an enum drawn from the plan, and `render_sql` turns it into
MySQL text deterministically. A table that is not in the plan cannot be typed;
a column that does not exist cannot be typed.

Two deliberate limits, both failing towards the old path rather than towards
wrong SQL:

- **Not every query fits.** CTEs, window functions, subqueries, UNION, CASE and
  self-joins have no representation here, and inventing one would trade a real
  expressiveness loss for a hallucination gain. The schema therefore carries an
  `expressible` flag the model sets to false, and the caller falls back to
  free-form generation. `soundwave_30` is full of such queries by construction.
- **Rendering is total or it declines.** `render_sql` returns None rather than
  emit a statement it is not sure of, so a malformed object becomes a fallback
  instead of a syntax error the verifier has to catch.

Everything here is a pure function of (query object, profile). No LLM call, no
I/O — so the renderer is unit-tested offline against hand-built objects.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.models.envelope import DBProfile

# Aggregate vocabulary. "" means the column is projected raw.
AGGREGATES = ("", "COUNT", "COUNT_DISTINCT", "SUM", "AVG", "MIN", "MAX")

# Comparison vocabulary. IS NULL / IS NOT NULL take no value — the single most
# common semantic error in the corpus is `= NULL`, and it is unsayable here.
OPERATORS = ("=", "!=", ">", "<", ">=", "<=", "IS NULL", "IS NOT NULL", "LIKE", "IN")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")

# Arithmetic tail for a projected expression: `AVG(trk_dur_ms)` in milliseconds
# is not the same answer as the same average in minutes, and §3.3 of the
# evaluation protocol scores unit mismatches as wrong. Enumerating identifiers
# alone cannot express `/ 60000.0`, so this one slot stays free text — narrowed
# to digits, operators and parentheses, which carries no identifier and so no
# hallucination surface.
_EXPR_SUFFIX_RE = re.compile(r"^[\d\s+\-*/().]+$")


def self_referencing_tables(profile: DBProfile) -> set[str]:
    """Tables with an FK edge to themselves (`genres.parent_genre_id`, …).

    A flat table list cannot express one table in two roles, so a question that
    needs a self-join must not take this path: it would render a single-role
    query that looks right and answers a different question. Detected from the
    profile rather than hardcoded, so a new database inherits the guard.
    """
    tables: set[str] = set()
    for src, tgt in profile.relationship_edges:
        src_table = src.split(".", 1)[0].lower()
        if src_table == tgt.split(".", 1)[0].lower():
            tables.add(src_table)
    return tables


def _date_columns(profile: DBProfile, tables: set[str]) -> list[str]:
    out: list[str] = []
    for table in profile.tables:
        if table.name.lower() not in tables:
            continue
        for column in table.columns:
            if any(kind in column.data_type.lower() for kind in ("date", "time")):
                out.append(f"{table.name}.{column.name}")
    return out


def build_query_schema(profile: DBProfile, plan: dict[str, Any]) -> dict[str, Any] | None:
    """JSON Schema whose enums are exactly the plan's tables, columns and edges.

    Returns None when the plan is too thin to constrain anything, in which case
    the caller keeps the free-form path.
    """
    tables = [t for t in plan.get("tables", []) if isinstance(t, str)]
    if not tables:
        return None
    lowered = {t.lower() for t in tables}
    columns = [
        f"{table.name}.{column.name}"
        for table in profile.tables
        if table.name.lower() in lowered
        for column in table.columns
    ]
    if not columns:
        return None

    edges = [e for e in plan.get("join_on", []) if isinstance(e, str)]
    aggregate_targets = columns + ["*"]
    date_columns = _date_columns(profile, lowered)

    select_item = {
        "type": "object",
        "properties": {
            "function": {"type": "string", "enum": list(AGGREGATES)},
            "column": {"type": "string", "enum": aggregate_targets},
            "expr_suffix": {"type": "string"},
            "alias": {"type": "string"},
        },
        "required": ["function", "column"],
    }
    condition = {
        "type": "object",
        "properties": {
            "column": {"type": "string", "enum": columns},
            "operator": {"type": "string", "enum": list(OPERATORS)},
            "value": {"type": "string"},
        },
        "required": ["column", "operator"],
    }
    having_item = {
        "type": "object",
        "properties": {
            "function": {"type": "string", "enum": [a for a in AGGREGATES if a]},
            "column": {"type": "string", "enum": aggregate_targets},
            "operator": {"type": "string", "enum": list(OPERATORS)},
            "value": {"type": "string"},
        },
        "required": ["function", "column", "operator"],
    }
    # ORDER BY references a SELECT position rather than repeating an expression:
    # "top artists by play count" orders by COUNT(*), which is not a column and
    # cannot come from the column enum. MySQL accepts positional ORDER BY, so
    # this stays inside the closed vocabulary instead of reopening it.
    order_item = {
        "type": "object",
        "properties": {
            "select_index": {"type": "integer"},
            "direction": {"type": "string", "enum": ["ASC", "DESC"]},
        },
        "required": ["select_index", "direction"],
    }

    # Property order is load-bearing. llama.cpp compiles the schema to a grammar
    # that emits keys in declaration order, so a leading `expressible` flag
    # forced the model to rule on the query's difficulty before it had composed
    # any of it — and it answered "too hard" every single time, including for
    # `SELECT name FROM subscription_plans WHERE has_downloads = 1`. The
    # fallback signal is therefore last (decided once the query is written),
    # optional, and phrased so that the neutral answer is the common one.
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "distinct": {"type": "boolean"},
            "select": {"type": "array", "items": select_item},
            "from": {"type": "string", "enum": tables},
            "joins": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "enum": tables},
                        "on": {"type": "string", "enum": edges or [""]},
                    },
                    "required": ["table", "on"],
                },
            },
            "where": {"type": "array", "items": condition},
            "group_by": {"type": "array", "items": {"type": "string", "enum": columns}},
            "having": {"type": "array", "items": having_item},
            "order_by": {"type": "array", "items": order_item},
            "limit": {"type": "integer"},
            "needs_advanced_sql": {"type": "boolean"},
        },
        "required": ["select", "from"],
    }
    if date_columns:
        # Named separately so a relative window can be applied deterministically
        # to the right column instead of being re-derived by the model.
        schema["properties"]["time_column"] = {"type": "string", "enum": date_columns}
    return schema


# -- rendering ----------------------------------------------------------------


def _quote(value: str) -> str:
    """Literal rendering: numbers bare, everything else single-quoted.

    Values are the one slot a grammar cannot constrain (they are free text), so
    this is where a coded value like `status = 'banned'` would still slip
    through. The prompt's coded-value line is what prevents that; here we only
    make sure the literal is syntactically well formed.
    """
    text = str(value).strip()
    # The model often supplies the literal already quoted, because that is what
    # it has seen in a million SELECT statements. Quoting it again produced
    # `'''album'''`, which is valid SQL matching nothing — three items in the
    # 2026-07-21 re-run silently returned 0 rows this way. Strip one balanced
    # layer before quoting; an interior apostrophe is still escaped below.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1].strip()
    if _NUMERIC_RE.match(text):
        return text
    if text.upper() in ("TRUE", "FALSE", "NULL"):
        return text.upper()
    return "'" + text.replace("'", "''") + "'"


def _render_expression(function: str, column: str) -> str | None:
    function = (function or "").upper()
    if column != "*" and not all(_IDENTIFIER_RE.match(part) for part in column.split(".")):
        return None
    if not function:
        return None if column == "*" else column
    if function == "COUNT_DISTINCT":
        return f"COUNT(DISTINCT {column})"
    if function not in AGGREGATES:
        return None
    if function != "COUNT" and column == "*":
        return None  # SUM(*) and friends are not SQL
    return f"{function}({column})"


_TRUE_WORDS = {"yes", "true", "y", "t"}
_FALSE_WORDS = {"no", "false", "n", "f"}
_BOOLEAN_TYPES = ("tinyint(1)", "boolean", "bool", "bit")


def _coerce_flag(value: str, data_type: str | None) -> str:
    """`has_downloads = 'Yes'` -> `has_downloads = 1` on a flag column.

    Not a semantic guess: against a TINYINT(1), the string 'Yes' matches
    nothing, so there is no reading under which it was the right literal. The
    model keeps producing it because the glossary spells the flags out in
    words ("is explicit content (1=yes, 0=no)") — which is the phrasing a human
    needs. Normalising the literal here lets both audiences be served.
    """
    if not data_type or not any(kind in data_type.lower() for kind in _BOOLEAN_TYPES):
        return value
    word = str(value).strip().strip("'\"").lower()
    if word in _TRUE_WORDS:
        return "1"
    if word in _FALSE_WORDS:
        return "0"
    return value


def _render_condition(item: dict[str, Any], types: dict[str, str]) -> str | None:
    column = item.get("column")
    operator = (item.get("operator") or "").upper()
    if not column or operator not in OPERATORS:
        return None
    if operator in ("IS NULL", "IS NOT NULL"):
        return f"{column} {operator}"
    value = item.get("value")
    if value is None or str(value).strip() == "":
        return None
    data_type = types.get(str(column).lower())
    if operator == "IN":
        parts = [p.strip() for p in str(value).split(",") if p.strip()]
        if not parts:
            return None
        rendered = ", ".join(_quote(_coerce_flag(p, data_type)) for p in parts)
        return f"{column} IN ({rendered})"
    return f"{column} {operator} {_quote(_coerce_flag(str(value), data_type))}"


def _table_of(column: str) -> str:
    return column.split(".", 1)[0].lower() if "." in column else ""


def _canonicalize(query: dict[str, Any], profile: DBProfile) -> dict[str, Any] | None:
    """Rewrite every identifier to the profile's own casing, or decline.

    SoundWave's DDL is all lowercase so nothing depends on this today, but Day
    4 introspects MySQL, where `lower_case_table_names=0` (the Linux default)
    makes table names case-sensitive. Normalising once here means a model that
    echoes `Users.Status` produces working SQL instead of a runtime error on
    one deployment and not the other. An identifier that matches nothing at all
    declines, which doubles as validation that the grammar held.
    """
    tables = {t.name.lower(): t.name for t in profile.tables}
    columns = {
        f"{t.name}.{c.name}".lower(): f"{t.name}.{c.name}"
        for t in profile.tables
        for c in t.columns
    }

    def table(name: Any) -> str | None:
        return tables.get(str(name).strip().lower()) if name else None

    def column(name: Any) -> str | None:
        text = str(name).strip()
        return text if text == "*" else columns.get(text.lower())

    out = dict(query)
    source = table(query.get("from"))
    if source is None:
        return None
    out["from"] = source

    joins = []
    for join in query.get("joins") or []:
        joined = table(join.get("table"))
        condition = str(join.get("on") or "")
        if joined is None or "=" not in condition:
            return None
        left, right = (part.strip() for part in condition.split("=", 1))
        left_column, right_column = column(left), column(right)
        if left_column is None or right_column is None:
            return None
        joins.append({"table": joined, "on": f"{left_column} = {right_column}"})
    out["joins"] = joins

    for field in ("select", "where", "having"):
        items = []
        for item in query.get(field) or []:
            if not isinstance(item, dict):
                return None
            canonical = column(item.get("column"))
            if canonical is None:
                return None
            items.append({**item, "column": canonical})
        out[field] = items

    group_by = []
    for name in query.get("group_by") or []:
        canonical = column(name)
        if canonical is None:
            return None
        group_by.append(canonical)
    out["group_by"] = group_by

    if query.get("time_column"):
        canonical = column(query["time_column"])
        if canonical is None:
            return None
        out["time_column"] = canonical
    return out


def render_sql(
    query: dict[str, Any],
    profile: DBProfile,
    time_predicate: str | None = None,
) -> str | None:
    """Render a query object to MySQL, or None if it cannot be rendered safely.

    `time_predicate` is a fully-formed predicate with a `<date_column>`
    placeholder (see `services/temporal.required_predicate`); it is substituted
    onto the object's `time_column` and ANDed in. Applying it here rather than
    asking the model for it is the whole point — the pilot showed the model
    inventing `played_at <= CURDATE()` filters nobody asked for.
    """
    if not isinstance(query, dict) or query.get("needs_advanced_sql"):
        return None
    canonical = _canonicalize(query, profile)
    if canonical is None:
        return None
    query = canonical

    source = query["from"]
    known_tables = {t.name.lower() for t in profile.tables}

    in_scope = {str(source).lower()}
    join_clauses: list[str] = []
    for join in query.get("joins") or []:
        table, condition = join.get("table"), join.get("on")
        if not table or not condition or not _IDENTIFIER_RE.match(str(table)):
            return None
        if str(table).lower() not in known_tables or "=" not in condition:
            return None
        if str(table).lower() in in_scope:
            # A self-join needs aliases, which this form does not carry. Decline
            # and let the free-form path handle it rather than emit a cartesian.
            return None
        in_scope.add(str(table).lower())
        join_clauses.append(f"JOIN {table} ON {condition}")

    select_parts: list[str] = []
    has_aggregate = False
    bare_columns: list[str] = []
    for item in query.get("select") or []:
        expression = _render_expression(item.get("function", ""), item.get("column", ""))
        if expression is None:
            return None
        column = item.get("column", "")
        if column != "*" and _table_of(column) not in in_scope:
            return None  # a column from a table nobody joined
        if item.get("function"):
            has_aggregate = True
        else:
            bare_columns.append(column)
        suffix = str(item.get("expr_suffix") or "").strip()
        if suffix:
            if not _EXPR_SUFFIX_RE.match(suffix):
                return None
            expression = f"{expression} {suffix}"
        alias = str(item.get("alias") or "").strip()
        if alias and _IDENTIFIER_RE.match(alias):
            expression = f"{expression} AS {alias}"
        select_parts.append(expression)
    if not select_parts:
        return None

    column_types = {
        f"{table.name}.{column.name}".lower(): column.data_type
        for table in profile.tables
        for column in table.columns
    }
    where_parts: list[str] = []
    for item in query.get("where") or []:
        rendered = _render_condition(item, column_types)
        if rendered is None:
            return None
        if _table_of(item.get("column", "")) not in in_scope:
            return None
        where_parts.append(rendered)

    if time_predicate:
        time_column = query.get("time_column")
        if not time_column or _table_of(str(time_column)) not in in_scope:
            # The window cannot be anchored to a column in scope; free-form
            # generation still has the STRICT time-constraint instruction.
            return None
        where_parts.append(time_predicate.replace("<date_column>", str(time_column)))

    group_parts = [c for c in (query.get("group_by") or []) if _table_of(c) in in_scope]
    # A grouped query that projects a bare column without grouping it is invalid
    # in ONLY_FULL_GROUP_BY and ambiguous everywhere else. The columns are
    # already chosen; completing the GROUP BY is deterministic, so do it here
    # rather than let the verifier reject an otherwise-correct query.
    if has_aggregate and bare_columns:
        for column in bare_columns:
            if column not in group_parts:
                group_parts.append(column)

    having_parts: list[str] = []
    for item in query.get("having") or []:
        expression = _render_expression(item.get("function", ""), item.get("column", ""))
        operator = (item.get("operator") or "").upper()
        if expression is None or operator not in OPERATORS:
            return None
        if operator in ("IS NULL", "IS NOT NULL"):
            having_parts.append(f"{expression} {operator}")
            continue
        value = item.get("value")
        if value is None or str(value).strip() == "":
            return None
        having_parts.append(f"{expression} {operator} {_quote(value)}")

    order_parts: list[str] = []
    for item in query.get("order_by") or []:
        index = item.get("select_index")
        direction = (item.get("direction") or "ASC").upper()
        if not isinstance(index, int) or not 1 <= index <= len(select_parts):
            return None
        if direction not in ("ASC", "DESC"):
            return None
        order_parts.append(f"{index} {direction}")

    clauses = [
        "SELECT " + ("DISTINCT " if query.get("distinct") else "") + ", ".join(select_parts),
        f"FROM {source}",
        *join_clauses,
    ]
    if where_parts:
        clauses.append("WHERE " + " AND ".join(where_parts))
    if group_parts:
        clauses.append("GROUP BY " + ", ".join(group_parts))
    if having_parts:
        clauses.append("HAVING " + " AND ".join(having_parts))
    if order_parts:
        clauses.append("ORDER BY " + ", ".join(order_parts))
    limit = query.get("limit")
    if isinstance(limit, int) and limit > 0:
        clauses.append(f"LIMIT {limit}")
    return "\n".join(clauses) + ";"
