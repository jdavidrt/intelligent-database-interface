"""The legal-SQL corpus — verification must not reject correct SQL.

V3 of the vocabulary contract: **SQL that follows every rule the prompt states
must pass verification.** The verifier's authority comes entirely from the rules
the generator was given; rule 4b is legitimate because SYSTEM_PROMPT states it,
but "no CTEs", "no filter predicates inside ON" and "no single-line SQL" were
enforced by accident, against SQL that obeyed every instruction it was given.

Those rejections are the expensive kind: there is no feedback message that can
fix them, because the model did nothing wrong. The regeneration loop burns a
full generate + 3-layer verify on a 3B model and then fails the same way, and
the user gets a wrong answer with a confident didactic explanation — the worst
outcome for a system whose stated purpose is teaching.

Every entry below was a real rejection at some point during the hardening
interlude. Entry 4 (CTE) was rejected by two independent bugs; entry 13 was
introduced *by the first draft of the fix* for entry 8, which is why this file
exists as a standing gate rather than a one-off check.

Paired with `MUST_REJECT` at the bottom: a change that makes the corpus pass by
making the rejections fail has not fixed anything. Both halves run together.
"""

from __future__ import annotations

import pytest

from backend.app.agents.verification import VerificationAgent
from backend.app.models.envelope import SqlCandidate


@pytest.fixture(scope="module")
def verifier(soundwave_connector) -> VerificationAgent:
    return VerificationAgent(soundwave_connector)


# -- The corpus: unambiguously correct SQL that must pass --------------------------

LEGAL_SQL: dict[str, str] = {
    # 1. Fully aliased multi-hop chain. `FROM artists AS a ... a.name` must never
    #    make the verifier look for a table named 'a' and call 'artists' invalid:
    #    sqlglot puts the table in exp.Table.name and the alias in .alias, and
    #    qualifiers resolve through scope.sources (keyed by alias when present).
    "aliased_ec08_chain": """
        SELECT a.name, COUNT(pe.event_id) AS plays
        FROM artists AS a
        JOIN track_artists AS ta ON ta.artist_id = a.artist_id
        JOIN play_events AS pe ON pe.track_id = ta.track_id
        GROUP BY a.artist_id, a.name
        ORDER BY plays DESC
        LIMIT 10;
    """,
    # 2. The nastiest alias case: an alias that shadows a *different* real table's
    #    name. 'tracks' here is play_events; a regex-based qualifier resolver
    #    would check event_id against the real tracks table and reject it.
    "alias_shadows_another_real_table": """
        SELECT tracks.event_id FROM play_events AS tracks LIMIT 5;
    """,
    # 3. No aliases, fully qualified — the shape deterministic assembly emits.
    "unaliased_fully_qualified": """
        SELECT artists.name, COUNT(play_events.event_id)
        FROM artists
        JOIN track_artists ON track_artists.artist_id = artists.artist_id
        JOIN play_events ON play_events.track_id = track_artists.track_id
        GROUP BY artists.name
        LIMIT 200;
    """,
    # 4. CTE. Rejected twice over: the flat exp.Table sweep called 'top' a
    #    hallucinated table, and the read-only guard's startswith("SELECT")
    #    called the whole statement non-SELECT because it starts with WITH.
    "cte_joined_back_to_a_real_table": """
        WITH top AS (
            SELECT ta.artist_id, COUNT(*) AS n
            FROM track_artists ta
            JOIN play_events pe ON pe.track_id = ta.track_id
            GROUP BY ta.artist_id
        )
        SELECT a.name, top.n
        FROM artists a
        JOIN top ON top.artist_id = a.artist_id
        ORDER BY top.n DESC
        LIMIT 10;
    """,
    # 5. Derived table — the alias has no real table behind it, same as a CTE.
    "derived_table": """
        SELECT a.name
        FROM artists a
        JOIN (SELECT ta.artist_id FROM track_artists ta) sub ON sub.artist_id = a.artist_id
        LIMIT 5;
    """,
    # 6. Correlated subquery reaching an outer alias — resolution must walk the
    #    scope's ancestor chain, not just its own sources.
    "correlated_subquery": """
        SELECT a.name
        FROM artists a
        WHERE EXISTS (SELECT 1 FROM track_artists ta WHERE ta.artist_id = a.artist_id)
        LIMIT 5;
    """,
    # 7. ON carrying the FK *and* a filter equality. Requiring every ON equality
    #    to be an FK edge rejected this; the schema has ten column names shared
    #    across tables with no FK between them (label, country, status, title...).
    "on_clause_with_secondary_non_key_equality": """
        SELECT a.name, al.title
        FROM artists a
        JOIN albums al ON al.artist_id = a.artist_id AND al.label = a.label
        LIMIT 10;
    """,
    "on_clause_with_secondary_date_equality": """
        SELECT t.title
        FROM tracks t
        JOIN albums al ON al.album_id = t.album_id AND al.release_date = t.release_date
        LIMIT 5;
    """,
    # 8/9. Single-line SQL. The old guard was `\\bWHERE\\b.*AGG\\(` — '.' does not
    #    match newlines, so the verdict depended on where the model broke lines.
    #    These are the two most common answer shapes in the project.
    "single_line_where_plus_having": (
        "SELECT a.name FROM artists a JOIN track_artists ta ON ta.artist_id = a.artist_id "
        "WHERE a.name IS NOT NULL GROUP BY a.name HAVING COUNT(*) > 5 LIMIT 10;"
    ),
    "single_line_where_plus_order_by_count": (
        "SELECT a.name, COUNT(pe.event_id) FROM artists a "
        "JOIN track_artists ta ON ta.artist_id = a.artist_id "
        "JOIN play_events pe ON pe.track_id = ta.track_id "
        "WHERE pe.event_type = 'play' GROUP BY a.name "
        "ORDER BY COUNT(pe.event_id) DESC LIMIT 10;"
    ),
    # 10. Self-join: one table, two roles. The FK graph cannot distinguish the
    #     roles, so rule 4b skips these — and the direct self-loop edge stays legal.
    "self_join_parent_child_genres": """
        SELECT child.name, parent.name AS parent_name
        FROM genres child
        JOIN genres parent ON child.parent_genre_id = parent.genre_id
        LIMIT 5;
    """,
    # 11. A join on a *derived* edge: both columns FK-chain to tracks.track_id, so
    #     the equality is exactly as sound as the two FKs it short-cuts — and it is
    #     the edge the planner itself emits for EC-08.
    "multi_hop_via_derived_edge": """
        SELECT a.name
        FROM track_artists ta
        JOIN play_events pe ON pe.track_id = ta.track_id
        JOIN artists a ON ta.artist_id = a.artist_id
        LIMIT 5;
    """,
    # 12. DISTINCT + LEFT JOIN + IS NULL — the EC-11 regex must not see "= NULL".
    "distinct_left_join_is_null": """
        SELECT DISTINCT a.name
        FROM artists a
        LEFT JOIN albums al ON al.artist_id = a.artist_id
        WHERE al.album_id IS NULL
        LIMIT 10;
    """,
    # 13. Aggregate inside a subquery in WHERE — legal, and the naive AST fix for
    #     entries 8/9 flagged it. The walk must stop at nested SELECT/Subquery.
    "aggregate_inside_where_subquery": """
        SELECT u.user_id
        FROM users u
        WHERE u.user_id IN (
            SELECT p.user_id FROM payments p GROUP BY p.user_id HAVING COUNT(*) > 5
        )
        LIMIT 10;
    """,
    # 14. Set operations are read-only; the AST read-only guard must allow them.
    "union_of_two_selects": """
        SELECT name FROM artists UNION SELECT name FROM users LIMIT 10;
    """,
}


# Entries whose correctness is interpretation-dependent: the SQL is right, but
# the schema cannot confirm the *reading*. These must verify as "caution" — never
# rejected, never a silent clean pass. See test_verification_caveats.py.
EXPECTED_CAUTION = {
    "self_join_parent_child_genres",  # parent/child direction is unknowable
    "cte_joined_back_to_a_real_table",  # 'top' is not a schema table
    "derived_table",  # 'sub' is not a schema table
}


@pytest.mark.parametrize("name", sorted(LEGAL_SQL))
def test_legal_sql_passes_every_layer(verifier, soundwave_profile, name):
    """Each layer separately, so a failure names the guilty one immediately."""
    sql = LEGAL_SQL[name].strip()

    semantic = verifier._layer_semantic(sql, soundwave_profile)
    assert semantic.passed, f"semantic layer false positive: {semantic.message}"

    sanity = verifier._layer_sanity(sql, soundwave_profile, None)
    assert sanity.passed, f"sanity layer false positive: {sanity.message}"


@pytest.mark.parametrize("name", sorted(LEGAL_SQL))
def test_legal_sql_passes_end_to_end(verifier, soundwave_profile, name):
    """The full chain, including the engine EXPLAIN probe — no repair proposed."""
    report = verifier.verify(SqlCandidate(sql=LEGAL_SQL[name].strip()), soundwave_profile)
    assert report.overall_passed, (
        f"syntax: {report.syntax.message} | semantic: {report.semantic.message} "
        f"| sanity: {report.sanity.message}"
    )
    assert report.repaired_sql is None


@pytest.mark.parametrize("name", sorted(LEGAL_SQL))
def test_legal_sql_has_the_expected_verdict(verifier, soundwave_profile, name):
    """Caveat noise is its own kind of false positive.

    A caveat that fires on ordinary SQL trains the user to ignore it, which
    costs exactly as much as a wrong rejection — so the corpus pins which
    entries may carry one and asserts the rest are clean."""
    report = verifier.verify(SqlCandidate(sql=LEGAL_SQL[name].strip()), soundwave_profile)
    expected = "caution" if name in EXPECTED_CAUTION else "pass"
    assert report.verdict == expected, f"verdict {report.verdict}, caveats: {report.caveats}"


# -- The other half: what must still be rejected -----------------------------------

MUST_REJECT: dict[str, tuple[str, str]] = {
    # (sql, expected substring of the message)
    "invented_join_key_between_real_columns": (
        "SELECT a.name FROM artists a JOIN play_events pe ON a.artist_id = pe.user_id LIMIT 5;",
        "Invented join key",
    ),
    "hallucinated_column": (
        "SELECT a.name FROM artists a JOIN play_events pe ON a.artist_id = pe.artist_id LIMIT 5;",
        "does not exist",
    ),
    "hallucinated_table": (
        "SELECT x.foo FROM not_a_table x LIMIT 5;",
        "Hallucinated table",
    ),
    "aggregate_in_where": (
        "SELECT a.name FROM artists a WHERE COUNT(a.artist_id) > 5 LIMIT 5;",
        "Aggregate function found in WHERE",
    ),
    # Rule 4b reads each JOIN's ON clause, so an implicit join had no ON to check
    # and bypassed the closed vocabulary entirely — this exact query passed.
    "comma_join_hiding_an_invented_key": (
        "SELECT a.name FROM artists a, play_events pe WHERE a.artist_id = pe.user_id LIMIT 5;",
        "Implicit (comma) join",
    ),
    "non_select_statement": ("DROP TABLE users;", "read-only guard"),
    # Stacked statements start with "SELECT", so the old string guard passed them.
    "stacked_statement_injection": ("SELECT 1; DROP TABLE users;", "read-only guard"),
    "delete_behind_a_cte": ("WITH t AS (SELECT 1) DELETE FROM users;", "read-only guard"),
    "equals_null": (
        "SELECT u.user_id FROM users u WHERE u.status = NULL LIMIT 5;",
        "IS NULL",
    ),
}


@pytest.mark.parametrize("name", sorted(MUST_REJECT))
def test_illegal_sql_is_still_rejected(verifier, soundwave_profile, name):
    """Loosening a check to remove a false positive must not open a hole."""
    sql, expected = MUST_REJECT[name]
    semantic = verifier._layer_semantic(sql, soundwave_profile)
    sanity = verifier._layer_sanity(sql, soundwave_profile, None)

    assert not (semantic.passed and sanity.passed), "illegal SQL passed verification"
    message = semantic.message if not semantic.passed else sanity.message
    assert expected in message, f"rejected for the wrong reason: {message}"


# -- Verifier/executor parity ------------------------------------------------------


@pytest.mark.parametrize("name", sorted(LEGAL_SQL))
def test_verified_sql_actually_executes(soundwave_connector, name):
    """The verifier passing is a promise the connector must be able to keep.

    These had their own copies of the read-only rule and disagreed: the verifier
    accepted `WITH ... SELECT` while `execute_read` raised on it, so a CTE query
    would have passed all three layers and then died at execution."""
    soundwave_connector.execute_read(LEGAL_SQL[name].strip())


@pytest.mark.parametrize("name", sorted(MUST_REJECT))
def test_rejected_sql_is_also_refused_by_the_executor(soundwave_connector, name):
    """Parity in the other direction, for the write/injection cases: anything the
    read-only guard rejects must never reach the engine."""
    sql = MUST_REJECT[name][0]
    if "read-only guard" not in MUST_REJECT[name][1]:
        pytest.skip("not a read-only-guard case — the executor legitimately runs it")
    with pytest.raises(ValueError):
        soundwave_connector.execute_read(sql)
