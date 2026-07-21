"""Structured SQL emission — SQL_HARDENING_PLAN Step 2.

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

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "expressible": {"type": "boolean"},
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
        },
        "required": ["expressible", "select", "from"],
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


def _render_condition(item: dict[str, Any]) -> str | None:
    column = item.get("column")
    operator = (item.get("operator") or "").upper()
    if not column or operator not in OPERATORS:
        return None
    if operator in ("IS NULL", "IS NOT NULL"):
        return f"{column} {operator}"
    value = item.get("value")
    if value is None or str(value).strip() == "":
        return None
    if operator == "IN":
        parts = [p.strip() for p in str(value).split(",") if p.strip()]
        if not parts:
            return None
        return f"{column} IN ({', '.join(_quote(p) for p in parts)})"
    return f"{column} {operator} {_quote(value)}"


def _table_of(column: str) -> str:
    return column.split(".", 1)[0].lower() if "." in column else ""


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
    if not isinstance(query, dict) or not query.get("expressible", True):
        return None

    source = query.get("from")
    if not source or not _IDENTIFIER_RE.match(str(source)):
        return None
    known_tables = {t.name.lower() for t in profile.tables}
    if str(source).lower() not in known_tables:
        return None

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
        alias = str(item.get("alias") or "").strip()
        if alias and _IDENTIFIER_RE.match(alias):
            expression = f"{expression} AS {alias}"
        select_parts.append(expression)
    if not select_parts:
        return None

    where_parts: list[str] = []
    for item in query.get("where") or []:
        rendered = _render_condition(item)
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
