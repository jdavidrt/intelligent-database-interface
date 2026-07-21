"""The vocabulary contract — prompt, planner and verifier must agree.

Three parties consult the "closed join vocabulary": the prompt
(`_build_schema_summary`), the planner (`JoinGraph.join_tree`) and the verifier
(rule 4b, via `JoinGraph.has_edge`). They are supposed to be the same
vocabulary. They were not:

- the planner emitted `play_events.playlist_id = playlists.forked_from_id`
  because self-referencing FKs merged the fork column into the identity
  column's equivalence class (V0);
- the prompt declared its 29 foreign keys exhaustive ("a join key not listed
  here does NOT exist") while the planner in the same prompt shipped one of the
  57 derived equalities and told the model to copy it verbatim (V2).

These are property tests over every 2- and 3-table combination in the live
profile, not fixed examples, so they re-run against whatever schema a connector
introspects — including Day 4's MySQL.
"""

from __future__ import annotations

from itertools import combinations

import pytest

from backend.app.agents.sql_generator import _build_schema_summary, _render_join_edges
from backend.app.services.db.join_graph import JoinGraph


@pytest.fixture(scope="module")
def graph(soundwave_profile) -> JoinGraph:
    return JoinGraph(soundwave_profile.relationship_edges)


@pytest.fixture(scope="module")
def table_sets(soundwave_profile) -> list[set[str]]:
    names = sorted(t.name.lower() for t in soundwave_profile.tables)
    return [set(c) for n in (2, 3) for c in combinations(names, n)]


def _split(edge: str) -> tuple[str, str]:
    left, right = edge.split("=", 1)
    return left.strip(), right.strip()


# -- V0: the vocabulary is correct --------------------------------------------------


def test_v0_self_referencing_fk_is_a_role_not_an_identity(graph):
    """A self-loop FK is a legal direct edge but must never merge equivalence
    classes — otherwise every user-FK column joins to the *referrer* column."""
    assert graph.has_edge("genres.parent_genre_id", "genres.genre_id")
    assert graph.has_edge("users.referred_by_user_id", "users.user_id")
    assert graph.has_edge("playlists.forked_from_id", "playlists.playlist_id")

    assert not graph.has_edge("payments.user_id", "users.referred_by_user_id")
    assert not graph.has_edge("play_events.user_id", "users.referred_by_user_id")
    assert not graph.has_edge("play_events.playlist_id", "playlists.forked_from_id")
    # ... while the real identity joins stay legal
    assert graph.has_edge("payments.user_id", "users.user_id")
    assert graph.has_edge("play_events.playlist_id", "playlists.playlist_id")


def test_v0_known_non_relationships_stay_illegal(graph):
    """The 2026-07-19 failure and its neighbours: plausible-looking pairs of
    real columns that no foreign key relates."""
    assert not graph.has_edge("play_events.artist_id", "artists.artist_id")  # column doesn't exist
    assert not graph.has_edge("artists.artist_id", "play_events.user_id")
    assert not graph.has_edge("albums.label", "artists.label")  # shared name, no FK
    assert not graph.has_edge("users.country", "artists.country")


def test_v0_edge_label_prefers_the_real_foreign_key(graph, soundwave_profile):
    """When a derived edge and a real FK connect the same table pair, the plan
    must name the FK — `payments.user_id = users.referred_by_user_id` sorted
    lexicographically before the real `= users.user_id`."""
    tree = graph.join_tree({"users", "payments", "subscription_plans"})
    assert tree is not None
    assert "payments.user_id = users.user_id" in tree[0]
    assert not any("referred_by_user_id" in edge for edge in tree[0])


def test_v0_playlists_to_tracks_uses_the_identity_column(graph):
    """Regression for the poisoned plan: routing playlists->tracks through the
    fork-lineage column silently returned near-empty results, with a *passing*
    verification chain, because rule 4b accepted its own poisoned vocabulary."""
    tree = graph.join_tree({"playlists", "tracks"})
    assert tree is not None
    assert "play_events.playlist_id = playlists.playlist_id" in tree[0]
    assert not any("forked_from" in edge for edge in tree[0])


def test_v0_ec08_chain_unchanged(graph):
    """The fixes above must be surgical: the canonical chain is byte-identical."""
    assert graph.join_tree({"artists", "play_events"}) == (
        [
            "track_artists.artist_id = artists.artist_id",
            "play_events.track_id = track_artists.track_id",
        ],
        {"artists", "track_artists", "play_events"},
    )


def test_v0_is_key_column_separates_join_keys_from_filters(graph):
    assert graph.is_key_column("artists.artist_id")
    assert graph.is_key_column("play_events.track_id")
    assert not graph.is_key_column("albums.label")
    assert not graph.is_key_column("artists.name")
    assert not graph.is_key_column("users.country")


# -- V1: Planner subset-of Verifier -------------------------------------------------


def test_v1_planner_never_plans_what_the_verifier_would_reject(graph, table_sets):
    """Every edge join_tree emits must satisfy has_edge. The system must never
    hand the model a plan its own rule-4b check would bounce — and after
    structured emission lands, that plan becomes the mandatory FROM/JOIN
    skeleton, so a violation here would be unfixable by the model."""
    for tables in table_sets:
        tree = graph.join_tree(tables)
        if tree is None:
            continue
        for edge in tree[0]:
            left, right = _split(edge)
            assert graph.has_edge(left, right), f"planner emitted a rejected edge: {edge}"


def test_v1_planned_edges_connect_the_planned_tables(graph, table_sets):
    """Every edge's two sides belong to tables the plan actually includes."""
    for tables in table_sets:
        tree = graph.join_tree(tables)
        if tree is None:
            continue
        edges, all_tables = tree
        for edge in edges:
            for side in _split(edge):
                owner = side.rsplit(".", 1)[0].lower()
                assert owner in all_tables, f"edge {edge} references unplanned table {owner}"


# -- V2: Prompt superset-of Planner -------------------------------------------------


def test_v2_every_planned_edge_is_declared_legal_to_the_model(graph, table_sets, soundwave_profile):
    """An edge is legal to the model either because it is on the prompt's
    foreign-key line, or because the plan block annotates it as a shortcut.
    Never neither — that is the contradiction that made the model choose."""
    fk_line = _build_schema_summary(soundwave_profile)
    for tables in table_sets:
        tree = graph.join_tree(tables)
        if tree is None:
            continue
        rendered = _render_join_edges(tree[0], soundwave_profile, "  ")
        for edge, line in zip(tree[0], rendered.split("\n")):
            declared_as_fk = edge in fk_line
            annotated = "shortcut through a shared key" in line
            assert declared_as_fk or annotated, f"edge presented as neither FK nor shortcut: {edge}"
            assert not (declared_as_fk and annotated), f"real FK wrongly annotated: {edge}"


def test_v2_prompt_no_longer_claims_the_fk_list_is_exhaustive(soundwave_profile):
    """The old wording ("a join key not listed here does NOT exist") was false:
    57 of the 86 legal equalities are not on that line."""
    summary = _build_schema_summary(soundwave_profile)
    assert "a join key not listed here does NOT exist" not in summary
    assert "or one of the equivalences given in the query plan below" in summary


def test_v2_derived_edges_outnumber_raw_fks(graph, soundwave_profile):
    """Sizes the problem V2 guards, and pins why the fix is annotation rather
    than dumping every legal equality into the prompt.

    29 raw FKs, 75 legal equalities total — so ~61 % of what the planner may
    emit is invisible on the prompt's foreign-key line. Rendering all 75 would
    bury the 29 the model needs most; annotating the handful that appear in a
    given plan costs nothing.

    (Before the self-loop fix this was 86: eleven of those edges were the
    poisoned ones that let payments join to a user's *referrer* and routed
    playlists->tracks through the fork-lineage column.)"""
    raw = len(soundwave_profile.relationship_edges)
    total = len(graph._edge_keys)
    assert raw == 29, raw
    assert total == 75, total
    assert total - raw > raw, "derived edges should outnumber raw FKs — the point of V2"
