"""Pins structured SQL emission (SQL_HARDENING_PLAN Step 2).

`render_sql` is a pure function of (query object, profile), so the whole
emission path is testable without an LLM, a grammar or a backend. That matters
more here than usual: the renderer's job is to be the component that *cannot*
produce an invalid identifier, and a bug in it would reintroduce exactly the
failure class the grammar was added to remove.

The declines are tested as carefully as the successes. Every `return None` in
the renderer hands the question back to free-form generation, so a decline that
should have been a render costs reach, and a render that should have been a
decline costs correctness.
"""

from __future__ import annotations

import os

import pytest

from backend.app.agents.sql_emitter import (
    build_query_schema,
    render_sql,
    self_referencing_tables,
)

# -- parked-module guard -------------------------------------------------------
#
# `sql_emitter` was unwired from the pipeline on 2026-07-21 (see its module
# docstring). A green suite asserting that unreachable code behaves correctly is
# worse than no suite: it reads as coverage of the running system and is not.
#
# The skip is conditional on *actual reachability* rather than a hardcoded flag,
# so re-wiring the emitter revives these 30 tests automatically. Nobody has to
# remember to delete a skip marker — the failure mode of forgetting is silent,
# which is the same trap being closed here.

_BACKEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app"
)


def _imported_by_pipeline() -> bool:
    """True if anything under backend/app references this module.

    A plain source scan, not an import graph: it needs no backend running, and
    a mention in a comment is a deliberate true — if someone wrote the name
    down, a human should decide whether these tests belong live again.
    """
    for root, _dirs, files in os.walk(_BACKEND):
        for name in files:
            if not name.endswith(".py") or name == "sql_emitter.py":
                continue
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                if "sql_emitter" in handle.read():
                    return True
    return False


pytestmark = pytest.mark.skipif(
    not _imported_by_pipeline(),
    reason=(
        "sql_emitter is parked — nothing under backend/app imports it, so these tests would "
        "assert unreachable code. They re-enable themselves when it is wired back in; see the "
        "module docstring for the two defects to fix first."
    ),
)


def _query(**overrides) -> dict:
    base = {
        "needs_advanced_sql": False,
        "select": [{"function": "", "column": "artists.name"}],
        "from": "artists",
    }
    base.update(overrides)
    return base


# -- rendering ----------------------------------------------------------------


def test_minimal_select(soundwave_profile) -> None:
    sql = render_sql(_query(), soundwave_profile)
    assert sql == "SELECT artists.name\nFROM artists;"


def test_string_value_is_quoted_and_number_is_not(soundwave_profile) -> None:
    """BIRD-008 emitted `status = 'banned'` against an integer column: valid
    SQL, zero rows, nothing for the verifier to reject. The literal's *form* is
    this module's job; choosing the code over the label is the prompt's."""
    sql = render_sql(
        _query(where=[{"column": "artists.country", "operator": "=", "value": "CO"}]),
        soundwave_profile,
    )
    assert "artists.country = 'CO'" in sql

    sql = render_sql(
        _query(
            select=[{"function": "COUNT", "column": "*"}],
            where=[{"column": "users.status", "operator": "=", "value": "2"}],
        )
        | {"from": "users"},
        soundwave_profile,
    )
    assert "users.status = 2" in sql


def test_already_quoted_values_are_not_quoted_twice(soundwave_profile) -> None:
    """`'album'` must not become `'''album'''`.

    The model supplies the literal pre-quoted because that is what SQL looks
    like. Re-quoting produced valid SQL that matched nothing, and three items
    in the 2026-07-21 re-run silently returned 0 rows — the worst failure shape
    there is, since nothing errors and nothing is flagged.
    """
    sql = render_sql(
        _query(where=[{"column": "albums.album_type", "operator": "=", "value": "'album'"}])
        | {"from": "albums", "select": [{"function": "", "column": "albums.title"}]},
        soundwave_profile,
    )
    assert "albums.album_type = 'album'" in sql


def test_interior_apostrophes_are_still_escaped(soundwave_profile) -> None:
    sql = render_sql(
        _query(where=[{"column": "artists.name", "operator": "=", "value": "Guns N' Roses"}]),
        soundwave_profile,
    )
    assert "artists.name = 'Guns N'' Roses'" in sql


def test_yes_no_literals_are_coerced_on_flag_columns(soundwave_profile) -> None:
    """`is_exp = 'Yes'` against a TINYINT(1) matches nothing, ever.

    The model reaches for the word because the glossary spells these flags out
    for humans ("is explicit content (1=yes, 0=no)"). Normalising the literal
    lets the glossary stay readable without costing every flag query.
    """
    sql = render_sql(
        _query(
            select=[{"function": "", "column": "tracks.title"}],
            where=[{"column": "tracks.is_exp", "operator": "=", "value": "Yes"}],
        )
        | {"from": "tracks"},
        soundwave_profile,
    )
    assert "tracks.is_exp = 1" in sql


def test_flag_coercion_does_not_touch_text_columns(soundwave_profile) -> None:
    """A country named 'No' would be a string, not a zero."""
    sql = render_sql(
        _query(where=[{"column": "artists.country", "operator": "=", "value": "No"}]),
        soundwave_profile,
    )
    assert "artists.country = 'No'" in sql


def test_is_null_takes_no_value(soundwave_profile) -> None:
    """`= NULL` is one of the EDR mutation operators — here it is unsayable."""
    sql = render_sql(
        _query(
            select=[{"function": "COUNT", "column": "*"}],
            where=[{"column": "tracks.album_id", "operator": "IS NULL"}],
        )
        | {"from": "tracks"},
        soundwave_profile,
    )
    assert sql == "SELECT COUNT(*)\nFROM tracks\nWHERE tracks.album_id IS NULL;"


def test_aggregate_functions_render(soundwave_profile) -> None:
    sql = render_sql(
        _query(select=[{"function": "AVG", "column": "tracks.trk_dur_ms", "alias": "avg_ms"}])
        | {"from": "tracks"},
        soundwave_profile,
    )
    assert sql == "SELECT AVG(tracks.trk_dur_ms) AS avg_ms\nFROM tracks;"


def test_count_distinct_renders_as_sql(soundwave_profile) -> None:
    sql = render_sql(
        _query(select=[{"function": "COUNT_DISTINCT", "column": "play_events.user_id"}])
        | {"from": "play_events"},
        soundwave_profile,
    )
    assert "COUNT(DISTINCT play_events.user_id)" in sql


def test_sum_of_star_is_declined(soundwave_profile) -> None:
    """`SUM(*)` is not SQL; only COUNT takes a star."""
    assert (
        render_sql(
            _query(select=[{"function": "SUM", "column": "*"}]) | {"from": "tracks"},
            soundwave_profile,
        )
        is None
    )


def test_group_by_is_completed_from_bare_columns(soundwave_profile) -> None:
    """A grouped query projecting an ungrouped column is invalid under
    ONLY_FULL_GROUP_BY. The columns are already chosen, so completing the
    GROUP BY is deterministic — better than letting the verifier reject it."""
    sql = render_sql(
        _query(
            select=[
                {"function": "", "column": "artists.name"},
                {"function": "COUNT", "column": "*"},
            ]
        )
        | {"from": "artists"},
        soundwave_profile,
    )
    assert "GROUP BY artists.name" in sql


def test_order_by_references_a_select_position(soundwave_profile) -> None:
    """Ordering by a computed COUNT is why positions exist: the aggregate is
    not a column and could not come from the column enum."""
    sql = render_sql(
        _query(
            select=[
                {"function": "", "column": "artists.name"},
                {"function": "COUNT", "column": "*"},
            ],
            order_by=[{"select_index": 2, "direction": "DESC"}],
            limit=5,
        )
        | {"from": "artists"},
        soundwave_profile,
    )
    assert sql.endswith("ORDER BY 2 DESC\nLIMIT 5;")


def test_out_of_range_order_index_declines(soundwave_profile) -> None:
    assert (
        render_sql(
            _query(order_by=[{"select_index": 7, "direction": "DESC"}]),
            soundwave_profile,
        )
        is None
    )


def test_join_renders_with_its_on_clause(soundwave_profile) -> None:
    sql = render_sql(
        _query(
            select=[{"function": "", "column": "tracks.title"}],
            joins=[
                {
                    "table": "track_artists",
                    "on": "tracks.track_id = track_artists.track_id",
                }
            ],
        )
        | {"from": "tracks"},
        soundwave_profile,
    )
    assert "JOIN track_artists ON tracks.track_id = track_artists.track_id" in sql


def test_time_predicate_is_applied_to_the_declared_column(soundwave_profile) -> None:
    """The window is applied here, not asked of the model.

    In the pilot the model invented `AND played_at <= CURDATE()` unprompted and
    lost two rows. Deterministic application removes that degree of freedom.
    """
    sql = render_sql(
        _query(select=[{"function": "COUNT", "column": "*"}])
        | {"from": "play_events", "time_column": "play_events.played_at"},
        soundwave_profile,
        time_predicate="<date_column> >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)",
    )
    assert "WHERE play_events.played_at >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)" in sql


def test_time_predicate_without_a_time_column_declines(soundwave_profile) -> None:
    """Rather than guess which column the window anchors to."""
    assert (
        render_sql(
            _query(select=[{"function": "COUNT", "column": "*"}]) | {"from": "play_events"},
            soundwave_profile,
            time_predicate="<date_column> >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)",
        )
        is None
    )


# -- declines -----------------------------------------------------------------


def test_inexpressible_is_declined(soundwave_profile) -> None:
    """The model's own escape hatch: CTEs, window functions, subqueries."""
    assert render_sql(_query(needs_advanced_sql=True), soundwave_profile) is None


def test_self_join_is_declined(soundwave_profile) -> None:
    """This form carries no aliases, so a self-join would render a cartesian.

    SPIDER-005 failed exactly this way under free-form emission — declining
    sends it to the path that can at least express it.
    """
    assert (
        render_sql(
            _query(joins=[{"table": "artists", "on": "artists.artist_id = artists.artist_id"}]),
            soundwave_profile,
        )
        is None
    )


def test_column_from_an_unjoined_table_is_declined(soundwave_profile) -> None:
    """The grammar limits columns to the plan's tables, not to the joined ones."""
    assert (
        render_sql(
            _query(select=[{"function": "", "column": "users.display_name"}]),
            soundwave_profile,
        )
        is None
    )


def test_unknown_table_is_declined(soundwave_profile) -> None:
    assert render_sql(_query() | {"from": "not_a_table"}, soundwave_profile) is None


def test_empty_select_is_declined(soundwave_profile) -> None:
    assert render_sql(_query(select=[]), soundwave_profile) is None


def test_non_dict_is_declined(soundwave_profile) -> None:
    assert render_sql("SELECT 1", soundwave_profile) is None  # type: ignore[arg-type]


def test_arithmetic_suffix_renders(soundwave_profile) -> None:
    """BIRD-003 wants minutes, not milliseconds.

    §3.3 of the protocol scores a unit mismatch as wrong and never coerces, so
    an enum-only SELECT that can say `AVG(trk_dur_ms)` but not `/ 60000.0`
    would fail the item it was meant to fix.
    """
    sql = render_sql(
        _query(
            select=[
                {
                    "function": "AVG",
                    "column": "tracks.trk_dur_ms",
                    "expr_suffix": "/ 60000.0",
                    "alias": "avg_minutes",
                }
            ]
        )
        | {"from": "tracks"},
        soundwave_profile,
    )
    assert sql == "SELECT AVG(tracks.trk_dur_ms) / 60000.0 AS avg_minutes\nFROM tracks;"


def test_expr_suffix_rejects_anything_but_arithmetic(soundwave_profile) -> None:
    """The one free-text slot carries no identifiers, so it carries no
    hallucination surface — and no injection surface either."""
    for suffix in ("; DROP TABLE users", "FROM users", "|| name", "/ trk_dur_ms"):
        assert (
            render_sql(
                _query(
                    select=[
                        {"function": "AVG", "column": "tracks.trk_dur_ms", "expr_suffix": suffix}
                    ]
                )
                | {"from": "tracks"},
                soundwave_profile,
            )
            is None
        ), suffix


def test_identifiers_are_normalised_to_profile_casing(soundwave_profile) -> None:
    """Day 4 introspects MySQL, where table names are case-sensitive under the
    Linux default `lower_case_table_names=0`."""
    sql = render_sql(
        _query(select=[{"function": "", "column": "ARTISTS.Name"}]) | {"from": "Artists"},
        soundwave_profile,
    )
    assert sql == "SELECT artists.name\nFROM artists;"


def test_unknown_column_is_declined(soundwave_profile) -> None:
    """`explicit` (SPIDER-008's invention) does not exist; `is_exp` does."""
    assert (
        render_sql(
            _query(select=[{"function": "", "column": "tracks.explicit"}]) | {"from": "tracks"},
            soundwave_profile,
        )
        is None
    )


# -- the self-join guard ------------------------------------------------------


def test_self_referencing_tables_are_detected_from_the_profile(soundwave_profile) -> None:
    """genres.parent_genre_id, users.referred_by_user_id, playlists.forked_from_id.

    Derived from the profile rather than hardcoded, so a new database folder
    inherits the guard without a code change.
    """
    assert self_referencing_tables(soundwave_profile) >= {"genres", "users", "playlists"}
    assert "artists" not in self_referencing_tables(soundwave_profile)


# -- schema construction ------------------------------------------------------


def test_schema_enums_are_scoped_to_the_plan(soundwave_profile) -> None:
    """The whole point: a table outside the plan is unsayable, not merely
    discouraged."""
    schema = build_query_schema(
        soundwave_profile,
        {"tables": ["subscription_plans"], "join_on": [], "output_columns": []},
    )
    assert schema["properties"]["from"]["enum"] == ["subscription_plans"]
    columns = schema["properties"]["group_by"]["items"]["enum"]
    assert "subscription_plans.has_downloads" in columns
    assert not any(c.startswith("subscriptions.") for c in columns)


def test_schema_without_tables_is_none(soundwave_profile) -> None:
    assert build_query_schema(soundwave_profile, {"tables": []}) is None


@pytest.mark.parametrize("table", ["artists", "tracks", "play_events"])
def test_every_planned_table_yields_a_usable_schema(soundwave_profile, table: str) -> None:
    schema = build_query_schema(soundwave_profile, {"tables": [table], "join_on": []})
    assert schema is not None
    assert schema["properties"]["from"]["enum"] == [table]
