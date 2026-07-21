"""Spider difficulty tiers, computed from reference SQL — never asserted.

EVALUATION_PROTOCOL.md §2.1 requires that the tier of a corpus item be "a
property of its SQL rather than the author's opinion", by reimplementing the
`eval_hardness` function from Spider's official `evaluation.py` and running it
over `reference_sql`. This module is that reimplementation.

WHAT THIS IS, PRECISELY
-----------------------
Spider's original operates on the dict produced by its own SQL parser, which
requires a Spider-format schema file and only accepts the SQL subset Spider's
grammar covers. This module reimplements the same *counting rules* over a
sqlglot AST. The binning thresholds in `eval_hardness()` are copied verbatim
from Spider; the component counts are recomputed against a different parse
tree. It is a faithful port of the rules, not a byte-for-byte port of the code,
and §2.1's guarantee (tier is a function of the SQL, fixed before any run) holds
either way.

Three constructs appear in the SoundWave corpora that Spider's grammar has no
representation for at all. Each is resolved here in the direction that keeps a
harder query from scoring as an easier one:

  * Window functions (RANK/DENSE_RANK OVER ...) — counted as aggregates, and
    their OVER(...) contents are searched for aggregates too. Spider would
    simply fail to parse these.
  * CTEs (WITH ... AS (SELECT ...)) — counted as nested SQL, i.e. component2,
    the same treatment Spider gives a subquery in WHERE.
  * Set operations (UNION/INTERSECT/EXCEPT) — component2, exactly as Spider.
    Spider counts them non-recursively (one set op = one nested unit) and so
    does this module.

SCOPE DISCIPLINE
----------------
Spider counts components on the *outermost* query only; anything nested is
counted once via component2 rather than having its internals folded into the
outer counts. Every walker here therefore stops at a subquery boundary. Getting
this wrong inflates every tier and is the single easiest way to break the
histogram silently, so `_walk_scoped` is the only traversal used.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

# Nodes that open a new query scope. Traversal stops here: their contents
# belong to a nested unit, not to the query being scored.
_SCOPE_BOUNDARIES = (exp.Select, exp.Subquery, exp.Union, exp.Except, exp.Intersect)

# Leaf predicates — Spider's "cond_unit". A flat count of these is what
# `len(sql['where']) > 1` tests in the original.
_PREDICATES = (
    exp.EQ,
    exp.NEQ,
    exp.GT,
    exp.GTE,
    exp.LT,
    exp.LTE,
    exp.Like,
    exp.ILike,
    exp.In,
    exp.Between,
    exp.Is,
)


def _walk_scoped(node: exp.Expression | None):
    """Yield every node at this query's own scope, stopping at nested queries.

    The root itself is always yielded even when it is a scope boundary; only
    *descendants* that open a scope are cut off.
    """
    if node is None:
        return
    yield node
    for child in node.args.values():
        for item in child if isinstance(child, list) else [child]:
            if isinstance(item, exp.Expression) and not isinstance(item, _SCOPE_BOUNDARIES):
                yield from _walk_scoped(item)


def _count(node: exp.Expression | None, types: tuple[type, ...]) -> int:
    return sum(1 for n in _walk_scoped(node) if isinstance(n, types))


def _clause(select: exp.Select, key: str) -> exp.Expression | None:
    """Read one clause off a Select.

    sqlglot 30 renamed two arg keys to dodge Python keywords: the FROM clause
    lives under `from_` and the WITH clause under `with_`, while `where`,
    `group`, `order`, `limit`, `having` and `joins` kept their names. A plain
    `args.get("from")` therefore returns None and silently under-counts, so both
    spellings are tried.
    """
    return select.args.get(key) or select.args.get(f"{key}_")


def _condition_sources(select: exp.Select) -> list[exp.Expression]:
    """WHERE, HAVING and join-ON — the three clauses Spider pools when counting
    OR tokens, LIKE operators and nested SQL."""
    sources: list[exp.Expression] = []
    for key in ("where", "having"):
        clause = _clause(select, key)
        if clause is not None:
            sources.append(clause)
    for join in select.args.get("joins") or []:
        on = join.args.get("on")
        if on is not None:
            sources.append(on)
    return sources


def count_component1(select: exp.Select) -> int:
    """WHERE / GROUP BY / ORDER BY / LIMIT / JOIN / OR / LIKE.

    One point each for the clause being present, one per join beyond the first
    table, one per OR token and one per LIKE operator.
    """
    count = 0
    for key in ("where", "group", "order", "limit"):
        if _clause(select, key) is not None:
            count += 1

    # table_units - 1, i.e. one point per JOIN. sqlglot represents a comma
    # join as a Join node with no ON, so both explicit and implicit joins land
    # in `joins` and one count covers them.
    count += len(select.args.get("joins") or [])

    for source in _condition_sources(select):
        count += _count(source, (exp.Or,))
        count += _count(source, (exp.Like, exp.ILike))
    return count


def count_component2(select: exp.Expression) -> int:
    """Nested SQL: subqueries inside conditions, CTEs, and set operations.

    Counted non-recursively, matching Spider's `len(get_nestedSQL(sql))`.
    """
    count = 0
    if isinstance(select, (exp.Union, exp.Except, exp.Intersect)):
        # Spider records one nested unit per set operation.
        return 1 + count_component2(select.this)

    if not isinstance(select, exp.Select):
        return 0

    # `.ctes` is sqlglot's public accessor and is stable across the arg-name
    # rename that made `args["with"]` return None in 30.x.
    count += len(select.ctes)

    for source in _condition_sources(select):
        # A scope boundary immediately below a condition is a nested query.
        for node in _walk_scoped(source):
            for child in node.args.values():
                for item in child if isinstance(child, list) else [child]:
                    if isinstance(item, (exp.Select, exp.Subquery)):
                        count += 1
    return count


def count_others(select: exp.Select) -> int:
    """Spider's "others": >1 aggregate, >1 select column, >1 WHERE condition,
    >1 GROUP BY column. One point each."""
    count = 0

    agg_count = 0
    for key in ("expressions", "where", "group", "order", "having"):
        clause = select.args.get(key)
        for item in clause if isinstance(clause, list) else [clause]:
            if isinstance(item, exp.Expression):
                agg_count += _count(item, (exp.AggFunc, exp.Window))
    if agg_count > 1:
        count += 1

    if len(select.expressions) > 1:
        count += 1

    where = _clause(select, "where")
    if where is not None and _count(where, _PREDICATES) > 1:
        count += 1

    group = _clause(select, "group")
    if group is not None and len(group.args.get("expressions") or []) > 1:
        count += 1

    return count


def _scoring_root(tree: exp.Expression) -> exp.Select | None:
    """The query whose components get counted.

    For a set operation Spider scores the left-hand SELECT and records the
    operation itself via component2; for `WITH ... SELECT` the outer SELECT is
    the subject and the CTEs are nested units.
    """
    node = tree
    while isinstance(node, (exp.Union, exp.Except, exp.Intersect)):
        node = node.this
    if isinstance(node, exp.Subquery):
        node = node.this
    return node if isinstance(node, exp.Select) else None


def components(sql: str, dialect: str = "mysql") -> tuple[int, int, int]:
    """(component1, component2, others) for one SQL string."""
    tree = sqlglot.parse_one(sql, read=dialect)
    root = _scoring_root(tree)
    if root is None:
        raise ValueError(f"not a SELECT statement: {sql[:80]!r}")
    return count_component1(root), count_component2(tree), count_others(root)


def eval_hardness(sql: str, dialect: str = "mysql") -> str:
    """Return 'easy' | 'medium' | 'hard' | 'extra'.

    The binning below is transcribed verbatim from Spider's
    `evaluation.py::Evaluator.eval_hardness`. Do not "simplify" the overlapping
    conditions — the order and the redundancy are Spider's, and matching its
    output is the entire point of this function.
    """
    comp1, comp2, others = components(sql, dialect=dialect)

    if comp1 <= 1 and others == 0 and comp2 == 0:
        return "easy"
    if (others <= 2 and comp1 <= 1 and comp2 == 0) or (comp1 <= 2 and others < 2 and comp2 == 0):
        return "medium"
    if (
        (others > 2 and comp1 <= 2 and comp2 == 0)
        or (2 < comp1 <= 3 and others <= 2 and comp2 == 0)
        or (comp1 <= 1 and others == 0 and comp2 <= 1)
    ):
        return "hard"
    return "extra"


# Spider's four tiers vs. the vocabularies the other corpora use. Each corpus
# keeps its own labels (§2.1 defines them per corpus); this maps them onto the
# computed Spider tier so one scorer can check all four histograms.
BIRD_FROM_SPIDER = {
    "easy": "simple",
    "medium": "simple",
    "hard": "moderate",
    "extra": "challenging",
}

SOUNDWAVE_FROM_SPIDER = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "extra": "Extra Hard",
}

# IDI-EXEC-75's low/medium/high. Chapter 1 §1.5 means these as *business*
# difficulty, which is not the same axis as SQL structure — an executive
# one-liner ("who's blowing up this year?") can be trivial to ask and hard to
# answer. Mapping them onto the computed Spider tier anyway is a deliberate
# trade: it costs some fidelity to Ch1's intent and buys the §2.1 guarantee that
# no tier is the author's unfalsifiable opinion. Recorded in §11 as a v1.2
# interpretation, not smuggled in.
EXEC_FROM_SPIDER = {
    "easy": "low",
    "medium": "medium",
    "hard": "high",
    "extra": "high",
}
