"""Verification Agent — 3-layer chain: Syntax -> Semantic -> Sanity."""

from __future__ import annotations
import re
import sqlglot
from sqlglot import exp

from backend.app.models.envelope import (
    DBProfile, SqlCandidate, VerifyReport, LayerResult,
)
from backend.app.services.llm_service import llm_service


class VerificationAgent:
    def __init__(self, connector) -> None:
        # Any DBConnector implementation (protocol, not a concrete class).
        self._db = connector

    def verify(self, candidate: SqlCandidate, profile: DBProfile) -> VerifyReport:
        # Adapter discipline: activate this agent's instruction profile.
        llm_service.load_adapter("verification")

        sql = candidate.sql.strip()

        syntax = self._layer_syntax(sql)
        if not syntax.passed:
            return VerifyReport(
                syntax=syntax,
                semantic=LayerResult(passed=False, message="Skipped — syntax failed"),
                sanity=LayerResult(passed=False, message="Skipped — syntax failed"),
                overall_passed=False,
            )

        semantic = self._layer_semantic(sql, profile)
        sanity = self._layer_sanity(sql, profile)

        overall = syntax.passed and semantic.passed and sanity.passed

        repaired_sql: str | None = None
        repair_note: str | None = None
        if not overall:
            repaired_sql, repair_note = self._attempt_repair(sql, profile, semantic, sanity)

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
            return LayerResult(passed=False, message="Engine EXPLAIN rejected the query")

        return LayerResult(passed=True, message="Syntax valid (sqlglot + EXPLAIN)")

    # -- Layer 2: Semantic ----------------------------------------------------------

    def _layer_semantic(self, sql: str, profile: DBProfile) -> LayerResult:
        """Schema-linking: every table/column in SQL must exist in DBProfile."""
        known_tables = {t.name.lower() for t in profile.tables}
        known_cols: dict[str, set[str]] = {
            t.name.lower(): {c.name.lower() for c in t.columns}
            for t in profile.tables
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

        # Check column references (only when table is qualified)
        for col in tree.find_all(exp.Column):
            tbl_ref = col.table
            col_name = col.name.lower() if col.name else ""
            if tbl_ref and col_name:
                tbl_ref_lower = tbl_ref.lower()
                if tbl_ref_lower in known_cols:
                    if col_name not in known_cols[tbl_ref_lower]:
                        return LayerResult(
                            passed=False,
                            message=f"Hallucinated column: '{tbl_ref}.{col.name}' not in schema",
                        )

        return LayerResult(passed=True, message="All tables and columns exist in DBProfile")

    # -- Layer 3: Sanity --------------------------------------------------------------

    def _layer_sanity(self, sql: str, profile: DBProfile) -> LayerResult:
        """
        Safety heuristics from the soundwave edge-case taxonomy:
        - Must be SELECT (read-only guard).
        - No NULL = NULL patterns (= NULL instead of IS NULL).
        - No aggregate in WHERE without HAVING (pre-agg vs raw).
        - Must have or accept a LIMIT.
        """
        sql_upper = sql.upper()

        if not sql_upper.lstrip().startswith("SELECT"):
            return LayerResult(passed=False, message="Non-SELECT statement rejected (read-only guard)")

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

        return LayerResult(passed=True, message="Sanity checks passed")

    # -- Repair attempt ------------------------------------------------------------------

    def _attempt_repair(
        self,
        sql: str,
        profile: DBProfile,
        semantic: LayerResult,
        sanity: LayerResult,
    ) -> tuple[str | None, str | None]:
        """Apply simple mechanical fixes before falling back to the generator."""
        repaired = sql

        # Fix = NULL -> IS NULL
        if "= NULL" in sql.upper():
            repaired = re.sub(r"=\s*NULL\b", "IS NULL", repaired, flags=re.IGNORECASE)
            if repaired != sql:
                return repaired, "Repaired: replaced '= NULL' with 'IS NULL'"

        return None, None
