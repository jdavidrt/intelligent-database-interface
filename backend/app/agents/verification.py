"""Verification Agent — 3-layer chain: Syntax -> Semantic -> Sanity."""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from backend.app.models.envelope import (
    DBProfile,
    Intent,
    LayerResult,
    SqlCandidate,
    VerifyReport,
)
from backend.app.services import temporal

# -- Temporal-grounding check (sanity layer) -----------------------------------------
# A relative time window in the question ("last 8 months", "this year") can only be
# answered by SQL whose date filter is anchored to the current date. A small local
# model that doesn't know "now" tends to substitute a fixed literal from its training
# era (YEAR(col) = 2024) — syntactically and semantically valid, factually wrong.
# Window parsing + strict unit rules live in services/temporal.py, shared with the
# SQL Generator so generation and verification can never drift apart.

# Dynamic now-anchors accepted by both MySQL and the FileConnector transpile path.
_NOW_ANCHOR_RE = re.compile(
    r"\b(?:CURDATE|NOW|SYSDATE|CURRENT_DATE|CURRENT_TIMESTAMP)\b",
    re.IGNORECASE,
)
# A hardcoded-year predicate — the exact wrong shape the repair rewrites.
_HARDCODED_YEAR_PRED_RE = re.compile(
    r"YEAR\(\s*([A-Za-z_][\w.]*)\s*\)\s*=\s*\d{4}\b", re.IGNORECASE
)
# Unit-smuggling shape: `YEAR(col) >= YEAR(CURDATE()) - 7` for "last 7 months" —
# anchored to now, but a 7-YEAR calendar filter. Rewritten by the repair.
_YEAR_ARITH_PRED_RE = re.compile(
    r"YEAR\(\s*([A-Za-z_][\w.]*)\s*\)\s*(?:>=|>|=)\s*YEAR\(\s*CURDATE\(\s*\)\s*\)\s*-\s*\d+\b",
    re.IGNORECASE,
)


def _question_text(intent: Intent | None) -> str:
    """Current-turn question text (+ extracted time_range). A relative phrase in
    an injected [History] segment belongs to an earlier, already-answered turn
    and must not influence checks on the current one."""
    if intent is None:
        return ""
    question = intent.raw_query or ""
    if "[Current]" in question:
        question = question.split("[Current]", 1)[-1]
    if intent.time_range:
        question = f"{question} {intent.time_range}"
    return question


class VerificationAgent:
    def __init__(self, connector) -> None:
        # Any DBConnector implementation (protocol, not a concrete class).
        self._db = connector

    def verify(
        self,
        candidate: SqlCandidate,
        profile: DBProfile,
        intent: Intent | None = None,
    ) -> VerifyReport:
        sql = candidate.sql.strip()

        syntax = self._layer_syntax(sql)
        if not syntax.passed and syntax.message.startswith("sqlglot parse error"):
            # Unparseable SQL — the AST-based layers can't run at all.
            return VerifyReport(
                syntax=syntax,
                semantic=LayerResult(passed=False, message="Skipped — syntax failed"),
                sanity=LayerResult(passed=False, message="Skipped — syntax failed"),
                overall_passed=False,
            )

        # Parse succeeded: semantic + sanity always run, even when the engine EXPLAIN
        # probe failed. A schema-linking error (e.g. an alias-qualified column that
        # doesn't belong to its table) must surface with the semantic layer's precise
        # didactic message — naming the table/alias and where the column really lives —
        # not only the engine's terse "no such column". The regeneration loop feeds on
        # exactly these messages.
        semantic = self._layer_semantic(sql, profile)
        sanity = self._layer_sanity(sql, profile, intent)

        overall = syntax.passed and semantic.passed and sanity.passed

        repaired_sql: str | None = None
        repair_note: str | None = None
        if not overall:
            repaired_sql, repair_note = self._attempt_repair(sql, profile, semantic, sanity, intent)

        # overall_passed stays False when a repair is proposed: the orchestrator
        # re-verifies the repaired SQL and only then swaps the candidate.
        return VerifyReport(
            syntax=syntax,
            semantic=semantic,
            sanity=sanity,
            overall_passed=overall,
            repaired_sql=repaired_sql,
            repair_explanation=repair_note,
        )

    # -- Layer 1: Syntax -----------------------------------------------------------

    def _layer_syntax(self, sql: str) -> LayerResult:
        """sqlglot parse (AST) + engine query-plan probe (no execution)."""
        # AST check — agents emit MySQL; parse with the MySQL dialect.
        try:
            sqlglot.parse_one(sql, dialect="mysql")
        except Exception as e:
            return LayerResult(passed=False, message=f"sqlglot parse error: {e}")

        # Engine probe (SQLite EXPLAIN QUERY PLAN via the file connector today,
        # MySQL EXPLAIN on Day 4 — same protocol method).
        if not self._db.explain(sql):
            detail = getattr(self._db, "last_explain_error", None)
            message = (
                f"Engine EXPLAIN rejected the query: {detail}"
                if detail
                else ("Engine EXPLAIN rejected the query")
            )
            return LayerResult(passed=False, message=message)

        return LayerResult(passed=True, message="Syntax valid (sqlglot + EXPLAIN)")

    # -- Layer 2: Semantic ----------------------------------------------------------

    def _layer_semantic(self, sql: str, profile: DBProfile) -> LayerResult:
        """Schema-linking: every table must exist in DBProfile, and every column
        reference must resolve to a table/alias actually present in that query
        scope's FROM/JOIN clauses AND exist on the resolved table.

        The original version only checked columns whose qualifier was a *real table
        name*, so alias-qualified columns (`pe.stream_count` with `play_events pe`)
        were silently skipped — a hallucinated column on a joined alias sailed
        through to execution. Scope-aware resolution (sqlglot traverse_scope) closes
        that hole and also handles subqueries, CTEs and correlated references.
        """
        known_tables = {t.name.lower() for t in profile.tables}
        known_cols: dict[str, set[str]] = {
            t.name.lower(): {c.name.lower() for c in t.columns} for t in profile.tables
        }

        try:
            tree = sqlglot.parse_one(sql, dialect="mysql")
        except Exception as e:
            return LayerResult(passed=False, message=f"Parse error in semantic layer: {e}")

        # Check table references
        for tbl in tree.find_all(exp.Table):
            name = tbl.name.lower()
            if name and name not in known_tables:
                return LayerResult(
                    passed=False,
                    message=f"Hallucinated table: '{tbl.name}' not in DBProfile",
                )

        try:
            scopes = traverse_scope(tree)
        except Exception as e:
            return LayerResult(passed=False, message=f"Scope analysis failed: {e}")

        # Per-scope source maps: qualifier (alias or table name, lowered) ->
        #   (real table name | None for subquery/CTE, set of valid columns | None if unknown)
        source_maps: dict[int, dict[str, tuple[str | None, set[str] | None]]] = {}
        for scope in scopes:
            sources: dict[str, tuple[str | None, set[str] | None]] = {}
            for alias, source in scope.sources.items():
                key = alias.lower()
                if isinstance(source, exp.Table):
                    tname = source.name.lower()
                    sources[key] = (tname, known_cols.get(tname))
                else:
                    # Subquery/CTE: its output projection is the column universe.
                    sources[key] = (None, self._scope_output_columns(source))
            source_maps[id(scope)] = sources

        for scope in scopes:
            sources = source_maps[id(scope)]
            from_list = ", ".join(sorted(sources)) or "(none)"
            # Explicit `AS` aliases only (MySQL lets GROUP BY/HAVING reference them);
            # passthrough column names must NOT whitelist themselves.
            alias_names = self._explicit_select_aliases(scope)

            # A correlated subquery may reference any ancestor's sources, so the
            # resolution chain for this scope is: own sources first, then ancestors'.
            chain: list[dict[str, tuple[str | None, set[str] | None]]] = []
            s = scope
            while s is not None:
                chain.append(source_maps.get(id(s), {}))
                s = getattr(s, "parent", None)

            for col in scope.columns:
                col_name = col.name.lower() if col.name else ""
                if not col_name or col_name == "*":
                    continue
                qualifier = col.table.lower() if col.table else ""

                if qualifier:
                    resolved = next((m[qualifier] for m in chain if qualifier in m), None)
                    if resolved is None:
                        return LayerResult(
                            passed=False,
                            message=(
                                f"Column '{col.table}.{col.name}' references '{col.table}', "
                                f"which is not among the tables/aliases present in this "
                                f"query's FROM/JOIN clauses ({from_list}) — every SELECT "
                                f"reference must correspond to a joined table"
                            ),
                        )
                    tname, valid_cols = resolved
                    if valid_cols is not None and col_name not in valid_cols:
                        where = f"table '{tname}'" if tname else f"subquery '{qualifier}'"
                        return LayerResult(
                            passed=False,
                            message=(
                                f"Column '{col.name}' does not exist in {where} "
                                f"(referenced as '{col.table}.{col.name}')"
                                f"{self._owning_tables_hint(col_name, known_cols)}"
                            ),
                        )
                else:
                    if col_name in alias_names:
                        continue
                    universes = [cols for m in chain for _, cols in m.values()]
                    if any(u is None for u in universes):
                        continue  # a source with unknowable output (e.g. SELECT *)
                    if not any(col_name in u for u in universes):
                        return LayerResult(
                            passed=False,
                            message=(
                                f"Column '{col.name}' does not exist in any table present "
                                f"in FROM/JOIN ({from_list})"
                                f"{self._owning_tables_hint(col_name, known_cols)}"
                            ),
                        )

        return LayerResult(
            passed=True,
            message="All column references resolve to tables present in FROM/JOIN",
        )

    @staticmethod
    def _explicit_select_aliases(scope) -> set[str]:
        """Names introduced with `AS` in this scope's SELECT list."""
        expression = getattr(scope, "expression", None)
        selects = getattr(expression, "selects", None) or []
        return {e.alias.lower() for e in selects if isinstance(e, exp.Alias) and e.alias}

    @staticmethod
    def _scope_output_columns(source) -> set[str] | None:
        """Output column names of a Scope (subquery/CTE/select). None = unknowable
        (e.g. the projection contains a star), which disables strict checking."""
        expression = getattr(source, "expression", None)
        if expression is None:
            return None
        try:
            names = expression.named_selects
        except Exception:
            return None
        if not names or any(n == "*" for n in names):
            return None
        return {n.lower() for n in names}

    @staticmethod
    def _owning_tables_hint(col_name: str, known_cols: dict[str, set[str]]) -> str:
        """Didactic breadcrumb: name the table(s) that actually own the column, so
        both the user and the regeneration loop know exactly what to join instead."""
        owners = sorted(t for t, cols in known_cols.items() if col_name in cols)
        return f" — it exists in: {', '.join(owners)}" if owners else ""

    # -- Layer 3: Sanity --------------------------------------------------------------

    def _layer_sanity(
        self, sql: str, profile: DBProfile, intent: Intent | None = None
    ) -> LayerResult:
        """
        Safety heuristics from the soundwave edge-case taxonomy:
        - Must be SELECT (read-only guard).
        - No NULL = NULL patterns (= NULL instead of IS NULL).
        - No aggregate in WHERE without HAVING (pre-agg vs raw).
        - Must have or accept a LIMIT.
        - Temporal grounding: a relative window in the question requires a
          CURDATE()/NOW()-anchored date filter in the SQL (needs `intent`).
        """
        sql_upper = sql.upper()

        if not sql_upper.lstrip().startswith("SELECT"):
            return LayerResult(
                passed=False, message="Non-SELECT statement rejected (read-only guard)"
            )

        # EC-11 heuristic: = NULL instead of IS NULL
        if re.search(r"=\s*NULL\b", sql, re.IGNORECASE):
            return LayerResult(
                passed=False,
                message="NULL comparison error: use IS NULL, not = NULL (EC-11)",
            )

        # Aggregate in WHERE clause (should be HAVING)
        if re.search(r"\bWHERE\b.*\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql, re.IGNORECASE):
            return LayerResult(
                passed=False,
                message="Aggregate function found in WHERE clause — use HAVING instead",
            )

        # Temporal grounding: relative window in the question, no now-anchor in the SQL.
        temporal = self._check_temporal_grounding(sql, intent)
        if temporal is not None:
            return temporal

        return LayerResult(passed=True, message="Sanity checks passed")

    @staticmethod
    def _check_temporal_grounding(sql: str, intent: Intent | None) -> LayerResult | None:
        """Two-step temporal check. Returns None when it passes or cannot run.

        1. Anchor: a relative window in the question requires CURDATE()/NOW()-
           anchored date arithmetic — the classic failure is `YEAR(col) = 2024`
           standing in for "the last 8 months".
        2. Unit fidelity (strict): a *sized* window ("last 7 months") requires an
           INTERVAL carrying that exact number and unit. An anchored-but-wrong-
           unit filter — `YEAR(col) >= YEAR(CURDATE()) - 7` for a 7-MONTH window —
           passed the anchor check and returned 7 YEARS of data; it fails here."""
        question = _question_text(intent)
        if not question:
            return None
        match = temporal.RELATIVE_WINDOW_RE.search(question)
        if not match:
            return None
        phrase = match.group(0)
        if not _NOW_ANCHOR_RE.search(sql):
            return LayerResult(
                passed=False,
                message=(
                    f"Temporal mismatch: the question asks for a relative window "
                    f"('{phrase}'), but the SQL has no CURDATE()/NOW()-anchored date "
                    f"filter — a hardcoded period like YEAR(col) = 2024 does not answer "
                    f"'{phrase}'. Use date arithmetic from the current date, e.g. "
                    f"col >= DATE_SUB(CURDATE(), INTERVAL 8 MONTH)."
                ),
            )
        window = temporal.extract_relative_window(question)
        if window is not None:
            mismatch = temporal.unit_mismatch(sql, *window)
            if mismatch is not None:
                return LayerResult(passed=False, message=mismatch)
        return None

    # -- Repair attempt ------------------------------------------------------------------

    def _attempt_repair(
        self,
        sql: str,
        profile: DBProfile,
        semantic: LayerResult,
        sanity: LayerResult,
        intent: Intent | None = None,
    ) -> tuple[str | None, str | None]:
        """Apply simple mechanical fixes before falling back to the generator."""
        repaired = sql

        # Fix = NULL -> IS NULL
        if "= NULL" in sql.upper():
            repaired = re.sub(r"=\s*NULL\b", "IS NULL", repaired, flags=re.IGNORECASE)
            if repaired != sql:
                return repaired, "Repaired: replaced '= NULL' with 'IS NULL'"

        # Temporal repair: the question asks for a relative window and the SQL's only
        # date filter is a hardcoded YEAR(col) = <literal> — rewrite that predicate
        # into a rolling window anchored to CURDATE(). Only fires when exactly one
        # such predicate exists (an unambiguous mechanical rewrite); anything more
        # complex falls through to the regeneration loop with the sanity message.
        if not sanity.passed and sanity.message.startswith("Temporal"):
            window = temporal.extract_relative_window(_question_text(intent))
            if window:
                n, unit = window
                # Shape 1: hardcoded literal — `YEAR(col) = 2024`.
                if len(_HARDCODED_YEAR_PRED_RE.findall(sql)) == 1:
                    repaired = _HARDCODED_YEAR_PRED_RE.sub(
                        rf"\1 >= DATE_SUB(CURDATE(), INTERVAL {n} {unit.upper()})", sql
                    )
                    return repaired, (
                        f"Repaired: replaced hardcoded YEAR(...) = <literal> with a rolling "
                        f"{n}-{unit} window anchored to CURDATE() — relative time windows "
                        f"must be computed from the current date, not a fixed year"
                    )
                # Shape 2: unit smuggling — `YEAR(col) >= YEAR(CURDATE()) - 7` for a
                # 7-MONTH window (anchored, but a years-sized calendar filter).
                if len(_YEAR_ARITH_PRED_RE.findall(sql)) == 1:
                    repaired = _YEAR_ARITH_PRED_RE.sub(
                        rf"\1 >= DATE_SUB(CURDATE(), INTERVAL {n} {unit.upper()})", sql
                    )
                    return repaired, (
                        f"Repaired: replaced YEAR() arithmetic with a rolling {n}-{unit} "
                        f"window anchored to CURDATE() — the question's unit ({unit}) must "
                        f"appear in the INTERVAL, never be converted to years"
                    )

        return None, None
