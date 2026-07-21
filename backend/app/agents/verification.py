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
from backend.app.services.db.join_graph import JoinGraph
from backend.app.services.sql_safety import is_read_only

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

        # Check table references.
        #
        # Two namespaces meet here and must not be confused:
        #   - schema objects (DBProfile.tables), and
        #   - names the query binds itself (CTEs, and table aliases).
        # Aliases are already safe and must stay that way: sqlglot puts the real
        # table in exp.Table.name and the alias in .alias, so `FROM artists AS a`
        # is checked as 'artists', never as 'a'. NEVER "fix" this by comparing
        # tbl.alias against known_tables, or by resolving qualifiers with a
        # regex — `a.name` would then report the real table `artists` as
        # hallucinated. Column qualifiers are resolved through scope.sources
        # below, which sqlglot keys by alias-when-present, for the same reason.
        # CTE references have no such fallback (`JOIN top ON ...` parses as a
        # Table named 'top'), so they are exempted explicitly.
        cte_names = {
            cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE) if cte.alias_or_name
        }
        for tbl in tree.find_all(exp.Table):
            name = tbl.name.lower()
            if name and name not in known_tables and name not in cte_names:
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

        # Rule 4b enforcement (closed join vocabulary): every JOIN ... ON equality
        # between columns of two different real tables must be an FK edge from
        # DBProfile.relationship_edges. Column existence was already validated
        # above, so this catches the subtler hallucination: a join key built from
        # two *real* columns that are not actually related (e.g.
        # `artists.artist_id = play_events.user_id`). The message carries the
        # legal multi-hop chain so the regeneration loop gets the fix, not just
        # the diagnosis.
        caveats: list[str] = []
        if profile.relationship_edges:
            graph = JoinGraph(profile.relationship_edges)
            violation = self._find_illegal_join_edge(scopes, source_maps, graph, caveats)
            if violation is not None:
                return violation
            caveats.extend(
                self._bridge_caveats(scopes, source_maps, graph, profile.join_preferences)
            )

        return LayerResult(
            passed=True,
            message="All column references resolve to tables present in FROM/JOIN",
            caveats=caveats,
        )

    @staticmethod
    def _bridge_caveats(
        scopes, source_maps, graph: JoinGraph, preferences: dict[str, str] | None = None
    ) -> list[str]:
        """Routes where an equally-good alternative bridge exists (0c).

        The FK graph cannot decide between "tracks IN a playlist"
        (playlist_tracks) and "tracks PLAYED FROM it" (play_events) — both are
        two hops through a junction table, so `_score` picks lexicographically.
        Rather than let that coin-flip pass as certainty, name the route taken
        and the alternatives; the user (or the survey's source_of_truth) is the
        only authority that can settle it.
        """
        out: list[str] = []
        seen: set[tuple[str, str]] = set()
        for scope in scopes:
            tables = sorted({t for t, _ in (source_maps.get(id(scope), {}) or {}).values() if t})
            for i, a in enumerate(tables):
                for b in tables[i + 1 :]:
                    if (a, b) in seen or graph.path(a, b) == []:
                        continue
                    routes = graph.ambiguous_bridges(a, b)
                    if len(routes) < 2:
                        continue
                    used = [r for r in routes if all(t in tables for t in r)]
                    if len(used) != 1:
                        continue  # no route taken, or several — nothing specific to say
                    seen.add((a, b))
                    # A survey entry means a human has settled this route for this
                    # database; the tie is no longer the schema's to call. Silent
                    # when the query took the declared route, still flagged when it
                    # took another (that IS worth saying).
                    preferred = (preferences or {}).get(f"{a}|{b}")
                    if preferred and preferred.lower() in used[0]:
                        continue
                    others = [" -> ".join(r) for r in routes if r != used[0]]
                    out.append(
                        f"Ambiguous join route: {a} and {b} were connected through "
                        f"{' -> '.join(used[0])}, but {' and '.join(others)} link them "
                        f"equally directly and answer a different question. The schema "
                        f"alone cannot say which reading you meant."
                    )
        return out

    @staticmethod
    def _cross_table_equalities(
        on: exp.Expression,
        sources: dict[str, tuple[str | None, set[str] | None]],
        caveats: list[str] | None = None,
    ) -> list[tuple[str, str, exp.Column, exp.Column]]:
        """Equalities in an ON clause that relate columns of two *different*
        real tables, as (qualified_left, qualified_right, left, right).

        Skips column-vs-literal filters and unqualified columns outright. The
        two cases the FK graph *cannot* judge — a self-join (one table, two
        roles) and a side that resolves to no real table (subquery, CTE, or an
        alias owned by an enclosing scope) — are reported through `caveats`
        instead of being silently dropped: "I could not check this" is a
        different statement from "this is fine"."""
        pairs: list[tuple[str, str, exp.Column, exp.Column]] = []
        for eq in on.find_all(exp.EQ):
            left, right = eq.this, eq.expression
            if not (isinstance(left, exp.Column) and isinstance(right, exp.Column)):
                continue
            lq = left.table.lower() if left.table else ""
            rq = right.table.lower() if right.table else ""
            if not lq or not rq:
                continue
            l_table = sources.get(lq, (None, None))[0]
            r_table = sources.get(rq, (None, None))[0]
            if l_table is not None and r_table is not None and l_table != r_table:
                pairs.append(
                    (
                        f"{l_table}.{left.name.lower()}",
                        f"{r_table}.{right.name.lower()}",
                        left,
                        right,
                    )
                )
            elif caveats is None:
                continue
            elif l_table is not None and l_table == r_table:
                # Self-join: `genres child JOIN genres parent ON
                # child.parent_genre_id = parent.genre_id`. Both sides are the
                # same table, so the FK graph — which knows tables, not roles —
                # cannot tell parent-of from child-of, nor which direction the
                # question wanted. Reversing the two columns yields SQL that is
                # equally legal and answers the opposite question.
                caveats.append(
                    f"Unverified self-join on '{l_table}': "
                    f"'{left.table}.{left.name} = {right.table}.{right.name}' relates the "
                    f"table to itself in two roles. The schema cannot confirm the "
                    f"direction — check that this is the intended one and not its reverse."
                )
            else:
                # One side is a subquery, a CTE, or an alias belonging to an
                # enclosing scope: there is no real table to look up, so rule 4b
                # has nothing to check against. Say so rather than pass silently.
                unresolved = left.table if l_table is None else right.table
                caveats.append(
                    f"Unverified join condition: "
                    f"'{left.table}.{left.name} = {right.table}.{right.name}' — "
                    f"'{unresolved}' is a subquery, CTE or outer-scope alias, not a schema "
                    f"table, so this join key could not be checked against the foreign keys."
                )
        return pairs

    @classmethod
    def _find_illegal_join_edge(
        cls,
        scopes,
        source_maps: dict[int, dict[str, tuple[str | None, set[str] | None]]],
        graph: JoinGraph,
        caveats: list[str] | None = None,
    ) -> LayerResult | None:
        """First JOIN whose ON clause is not anchored on a real relationship.

        Checks the JOIN, not each equality. An ON clause carries at most one
        relationship and any number of filters —
        `ON al.artist_id = a.artist_id AND al.label = a.label` is ordinary,
        legal SQL — so requiring *every* equality to be an FK edge rejected
        correct queries (albums/artists share a non-key `label` column, as do
        nine other column names in this schema). Requiring at least *one* still
        catches the failure this rule exists for, because an invented join key
        is the join's only equality.
        """
        for scope in scopes:
            sources = source_maps.get(id(scope), {})
            expression = getattr(scope, "expression", None)
            joins = (getattr(expression, "args", None) or {}).get("joins") or []
            for join in joins:
                on = join.args.get("on")
                if on is None:
                    continue
                pairs = cls._cross_table_equalities(on, sources, caveats)
                if not pairs:
                    continue  # nothing relating two real tables (e.g. ON 1 = 1)
                if any(graph.has_edge(a, b) for a, b, _, _ in pairs):
                    # Anchored on a real relationship; the remaining equalities are
                    # filters and none of rule 4b's business — `ON al.artist_id =
                    # a.artist_id AND al.label = a.label` is ordinary SQL. But an
                    # extra equality between two *key* columns that no FK relates
                    # (`AND al.album_id = a.artist_id`) is not a plausible filter:
                    # comparing two identifiers from different key families is
                    # either a mistake or an intent the schema can't express.
                    # Flag it without blocking — some models legitimately narrow a
                    # join this way, and the anchor already guarantees the
                    # relationship is real.
                    if caveats is not None:
                        for a, b, left, right in pairs:
                            if graph.has_edge(a, b):
                                continue
                            if graph.is_key_column(a) and graph.is_key_column(b):
                                caveats.append(
                                    f"Unverified extra join condition: "
                                    f"'{left.table}.{left.name} = {right.table}.{right.name}' "
                                    f"compares two key columns that no foreign key relates "
                                    f"({a} vs {b}). The join itself is anchored on a real "
                                    f"relationship, so this only narrows the result — but it "
                                    f"may not mean what it looks like."
                                )
                    continue
                # Unanchored. Report the most key-like equality so the message
                # names the columns the model actually meant as the join key.
                a, b, left, right = max(
                    pairs,
                    key=lambda p: (graph.is_key_column(p[0]) + graph.is_key_column(p[1])),
                )
                l_table, r_table = a.rsplit(".", 1)[0], b.rsplit(".", 1)[0]
                legal = graph.path(l_table, r_table)
                if legal:
                    hint = (
                        f" The legal join chain from {l_table} to {r_table} is: "
                        + " ; ".join(legal)
                        + " — join through the intermediate table(s), copying these "
                        "ON clauses verbatim."
                    )
                else:
                    hint = (
                        f" No foreign-key path connects {l_table} and {r_table} at "
                        "all — one of them is the wrong table for this question."
                    )
                return LayerResult(
                    passed=False,
                    message=(
                        f"Invented join key: '{left.table}.{left.name} = "
                        f"{right.table}.{right.name}' is not a relationship in the "
                        f"schema — no foreign key links {a} to {b}, directly or "
                        f"transitively.{hint}"
                    ),
                )
        return None

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
        - No implicit (comma) joins — SYSTEM_PROMPT asks for explicit JOIN ... ON.
        - Must have or accept a LIMIT.
        - Temporal grounding: a relative window in the question requires a
          CURDATE()/NOW()-anchored date filter in the SQL (needs `intent`).
        """
        try:
            tree = sqlglot.parse_one(sql, dialect="mysql")
        except Exception:
            tree = None  # unparseable; the string guard below is the only check left

        # Read-only guard — the same function the connector calls before executing
        # (services/sql_safety.py), so verification can never green-light a
        # statement execution refuses, or vice versa. It is strictly stronger than
        # the startswith("SELECT") check it replaces: `WITH ... SELECT` is now
        # correctly a SELECT, and `SELECT 1; DROP TABLE users` is now correctly not.
        if not is_read_only(sql):
            return LayerResult(
                passed=False, message="Non-SELECT statement rejected (read-only guard)"
            )

        # EC-11 heuristic: = NULL instead of IS NULL
        if re.search(r"=\s*NULL\b", sql, re.IGNORECASE):
            return LayerResult(
                passed=False,
                message="NULL comparison error: use IS NULL, not = NULL (EC-11)",
            )

        if tree is not None:
            aggregate_in_where = self._find_aggregate_in_where(tree)
            if aggregate_in_where is not None:
                return aggregate_in_where
            implicit_join = self._find_implicit_join(tree)
            if implicit_join is not None:
                return implicit_join

        # Temporal grounding: relative window in the question, no now-anchor in the SQL.
        temporal = self._check_temporal_grounding(sql, intent)
        if temporal is not None:
            return temporal

        return LayerResult(passed=True, message="Sanity checks passed")

    @staticmethod
    def _find_aggregate_in_where(tree: exp.Expression) -> LayerResult | None:
        """Aggregate used as a WHERE predicate (belongs in HAVING), or None.

        Two traps this avoids, both of which a regex over the raw SQL walked
        straight into:

        1. `\\bWHERE\\b.*AGG\\(` never matched across newlines, so the verdict
           depended on where the model happened to break lines — the same query
           passed multi-line and failed single-line.
        2. An aggregate inside a *subquery* in the WHERE is legal:
           `WHERE user_id IN (SELECT ... HAVING COUNT(*) > 5)` is correct SQL.
           So the walk stops at any nested SELECT/subquery and only reports
           aggregates belonging to the WHERE's own scope.
        """
        for where in tree.find_all(exp.Where):
            for node in where.walk():
                if not isinstance(node, exp.AggFunc):
                    continue
                parent, nested = node.parent, False
                while parent is not None and parent is not where:
                    if isinstance(parent, (exp.Select, exp.Subquery)):
                        nested = True
                        break
                    parent = parent.parent
                if not nested:
                    return LayerResult(
                        passed=False,
                        message=("Aggregate function found in WHERE clause — use HAVING instead"),
                    )
        return None

    @staticmethod
    def _find_implicit_join(tree: exp.Expression) -> LayerResult | None:
        """Reject comma joins (`FROM a, b WHERE a.x = b.y`), or None.

        Not a style rule: rule 4b reads each JOIN's ON clause, so an
        implicit join has no ON to check and bypasses the closed join
        vocabulary entirely — `FROM artists a, play_events pe WHERE
        a.artist_id = pe.user_id` is exactly the invented key rule 4b exists to
        catch, and it passed. SYSTEM_PROMPT already asks for explicit
        `JOIN ... ON`, so this enforces a rule the generator was given, and the
        message tells it precisely what to do differently.
        """
        # sqlglot keeps the first FROM source in args["from"] and each
        # comma-separated one in args["joins"] as a join with no "on", no side
        # and no kind — which is exactly what distinguishes it from an explicit
        # CROSS/NATURAL JOIN (kind set) or a LEFT/RIGHT JOIN (side set).
        for select in tree.find_all(exp.Select):
            for join in select.args.get("joins") or []:
                if join.args.get("on") is not None or join.args.get("using"):
                    continue
                if (join.side or join.kind or "").strip():
                    continue  # CROSS JOIN / NATURAL JOIN — explicit and deliberate
                table = join.this
                name = table.name if isinstance(table, exp.Table) else ""
                return LayerResult(
                    passed=False,
                    message=(
                        f"Implicit (comma) join on '{name or 'a table'}': every "
                        "relationship must be written as an explicit JOIN ... ON so its "
                        "join key can be verified against the schema. Rewrite as "
                        "`FROM <table> JOIN <table> ON <one of the listed join paths>`."
                    ),
                )
        return None

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
