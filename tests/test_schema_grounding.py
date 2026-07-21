"""Schema grounding — closed join vocabulary, deterministic FK paths, plan step.

Born from a real failure: "who are the most reproduced artists of the last
year?" generated `JOIN play_events pe ON a.artist_id = pe.artist_id` —
`play_events` has no `artist_id`; the legal route is the EC-08 multi-hop chain
artists -> track_artists -> tracks -> play_events. These tests pin down:

1. JoinGraph resolves that chain deterministically from relationship_edges.
2. The semantic layer rejects invented join keys even when BOTH columns exist
   (the hole rule 4b left open), naming the legal chain in its message.
3. The SQL Generator injects the precomputed chain into its prompt, and the
   constrained-decoding plan step builds enums strictly from the schema.
"""

from __future__ import annotations

import pytest

from backend.app.agents.sql_generator import (
    PLAN_SYSTEM_PROMPT,
    SQLGenerator,
    _linked_tables,
    _tables_in_feedback,
)
from backend.app.agents.verification import VerificationAgent
from backend.app.config import settings
from backend.app.models.envelope import Intent
from backend.app.services.db.join_graph import JoinGraph
from backend.app.services.llm_service import llm_service

FAILING_SQL = """\
SELECT a.name AS artist_name, COUNT(pe.event_id) AS play_count
FROM artists a JOIN play_events pe ON a.artist_id = pe.artist_id
WHERE YEAR(pe.played_at) = 2025
GROUP BY a.artist_id, a.name ORDER BY play_count DESC LIMIT 10;"""

CORRECT_SQL = """\
SELECT a.name AS artist_name, COUNT(pe.event_id) AS play_count
FROM play_events pe
JOIN tracks t ON pe.track_id = t.track_id
JOIN track_artists ta ON ta.track_id = t.track_id
JOIN artists a ON ta.artist_id = a.artist_id
WHERE pe.event_type = 'play'
GROUP BY a.artist_id, a.name ORDER BY play_count DESC LIMIT 10;"""

CANNED_GENERATION = "### Rationale\nplan followed.\n\n### SQL\n```sql\nSELECT 1;\n```"

CANNED_PLAN_JSON = (
    '{"tables": ["artists", "play_events"], "join_on": [], ' '"output_columns": ["artists.name"]}'
)


@pytest.fixture
def graph(soundwave_profile) -> JoinGraph:
    return JoinGraph(soundwave_profile.relationship_edges)


@pytest.fixture
def verifier(soundwave_connector) -> VerificationAgent:
    return VerificationAgent(soundwave_connector)


# -- 1. JoinGraph ------------------------------------------------------------------


def test_no_direct_edge_artists_play_events(graph):
    assert not graph.has_edge("play_events.artist_id", "artists.artist_id")
    assert not graph.has_edge("artists.artist_id", "play_events.user_id")
    assert graph.has_edge("play_events.track_id", "tracks.track_id")
    # Direction-independent
    assert graph.has_edge("tracks.track_id", "play_events.track_id")
    # Transitive: both FK-chain to tracks.track_id — the EC-08 recommended join
    assert graph.has_edge("track_artists.track_id", "play_events.track_id")


def test_path_artists_to_play_events_is_ec08_chain(graph):
    """The canonical chain the instruction profile recommends:
    play_events -> track_artists -> artists (2 joins, via the bridge —
    NOT via albums, which drops singles and featured credits)."""
    chain = graph.path("artists", "play_events")
    assert chain is not None and len(chain) == 2
    joined = " ; ".join(chain)
    assert "track_artists" in joined
    assert "play_events.track_id" in joined
    assert "albums" not in joined


def test_join_tree_pulls_in_intermediates(graph):
    tree = graph.join_tree({"artists", "play_events"})
    assert tree is not None
    edges, tables = tree
    assert {"artists", "track_artists", "play_events"} <= tables
    assert "albums" not in tables
    assert len(edges) == 2


def test_join_tree_single_table(graph):
    assert graph.join_tree({"artists"}) == ([], {"artists"})


def test_self_referencing_fk_does_not_leak_into_other_joins(graph):
    """A self-loop FK (users.referred_by_user_id -> users.user_id) is a *role*
    edge, not an identity. Merging the two columns into one equivalence class
    made every user-FK column in the schema join-legal against the referrer
    column, and materialised that as a real graph edge — so a query joining
    payments to the *referrer* of a user passed verification silently."""
    assert graph.has_edge("users.referred_by_user_id", "users.user_id")  # direct: legal
    assert graph.has_edge("genres.parent_genre_id", "genres.genre_id")
    assert not graph.has_edge("payments.user_id", "users.referred_by_user_id")
    assert graph.has_edge("payments.user_id", "users.user_id")


def test_join_tree_prefers_the_real_fk_over_a_derived_edge(graph):
    """`payments.user_id = users.referred_by_user_id` sorted lexicographically
    before the real `= users.user_id`, so the plan named the fork/referrer
    column. _edge_label now ranks real FKs first."""
    tree = graph.join_tree({"users", "payments", "subscription_plans"})
    assert tree is not None
    assert "payments.user_id = users.user_id" in tree[0]
    assert not any("referred_by" in edge for edge in tree[0])


def test_join_tree_playlists_to_tracks_uses_playlist_identity(graph):
    """The same poisoning, but reaching the prompt as a LOCKED plan: routing
    playlists->tracks through playlists.forked_from_id filtered on fork lineage
    instead of playlist identity, returning near-empty results with a passing
    verification chain."""
    tree = graph.join_tree({"playlists", "tracks"})
    assert tree is not None
    assert "play_events.playlist_id = playlists.playlist_id" in tree[0]
    assert not any("forked_from" in edge for edge in tree[0])


def test_ec08_chain_is_unchanged_by_the_self_loop_fix(graph):
    """The fix must be surgical — this is the chain everything else depends on."""
    assert graph.join_tree({"artists", "play_events"}) == (
        [
            "track_artists.artist_id = artists.artist_id",
            "play_events.track_id = track_artists.track_id",
        ],
        {"artists", "track_artists", "play_events"},
    )


def test_is_key_column_distinguishes_join_keys_from_filter_columns(graph):
    """Lets the verifier tell `al.artist_id = a.artist_id` (a relationship)
    from `al.label = a.label` (a filter) inside one ON clause."""
    assert graph.is_key_column("artists.artist_id")
    assert not graph.is_key_column("albums.label")


# -- 2. Verifier: closed join vocabulary -------------------------------------------


def test_semantic_rejects_hallucinated_column(verifier, soundwave_profile):
    """The original failure: pe.artist_id does not exist at all."""
    res = verifier._layer_semantic(FAILING_SQL, soundwave_profile)
    assert not res.passed
    assert "does not exist" in res.message
    assert "track_artists" in res.message  # owner hint names where it really lives


def test_semantic_rejects_invented_join_key_between_real_columns(verifier, soundwave_profile):
    """Rule 4b enforcement: both columns exist, but no FK relates them —
    this sailed through the old column-existence-only check."""
    sql = "SELECT a.name FROM artists a " "JOIN play_events pe ON a.artist_id = pe.user_id LIMIT 5;"
    res = verifier._layer_semantic(sql, soundwave_profile)
    assert not res.passed
    assert "Invented join key" in res.message
    # The didactic hint carries the legal chain through the bridge table
    assert "track_artists" in res.message


def test_semantic_accepts_legal_multi_hop_chain(verifier, soundwave_profile):
    res = verifier._layer_semantic(CORRECT_SQL, soundwave_profile)
    assert res.passed, res.message


def test_semantic_accepts_self_join(verifier, soundwave_profile):
    sql = (
        "SELECT child.name FROM genres child "
        "JOIN genres parent ON child.parent_genre_id = parent.genre_id LIMIT 5;"
    )
    res = verifier._layer_semantic(sql, soundwave_profile)
    assert res.passed, res.message


def test_full_verify_blocks_invented_join_key(verifier, soundwave_profile):
    """End-to-end: SQLite happily EXPLAINs a cross-join on unrelated keys —
    only the new edge check stops it from executing and returning garbage."""
    from backend.app.models.envelope import SqlCandidate

    candidate = SqlCandidate(
        sql=(
            "SELECT a.name FROM artists a "
            "JOIN play_events pe ON a.artist_id = pe.user_id LIMIT 5;"
        )
    )
    report = verifier.verify(candidate, soundwave_profile, intent=None)
    assert not report.overall_passed
    assert "Invented join key" in report.semantic.message


# -- 3. Generator: plan injection ---------------------------------------------------


def _capture_generation(monkeypatch):
    """Patch chat_with_meta, capturing the prompt and returning a canned answer."""
    captured: dict = {}

    def fake_chat_with_meta(messages, temperature=0.3, timeout=90):
        captured["prompt"] = messages[-1]["content"]
        return CANNED_GENERATION, {"elapsed_ms": 0}

    monkeypatch.setattr(llm_service, "chat_with_meta", fake_chat_with_meta)
    return captured


def test_linked_tables_matches_names_in_question(soundwave_profile):
    intent = Intent(
        raw_query="which artists appear in play_events most often?",
        entities=["artists", "play_events"],
    )
    assert _linked_tables(intent, soundwave_profile) == {"artists", "play_events"}


def test_generator_injects_precomputed_join_plan(
    monkeypatch, soundwave_profile, patched_vector_context
):
    """Level 1 (plan step disabled by conftest): the FK-derived chain must appear
    verbatim in the prompt so the model never derives the multi-hop join alone."""
    captured = _capture_generation(monkeypatch)
    intent = Intent(
        raw_query="who are the most played artists?",
        entities=["artists", "play_events"],
        plain_restatement="Most played artists",
    )
    SQLGenerator().generate(intent, soundwave_profile)
    prompt = captured["prompt"]
    assert "Precomputed join plan" in prompt
    assert "track_artists" in prompt and "tracks" in prompt


def test_constrained_plan_builds_enums_from_schema(monkeypatch, soundwave_profile):
    """Level 2: the JSON Schema handed to llama.cpp must enumerate exactly the
    schema's tables — the grammar makes out-of-vocabulary output impossible."""
    monkeypatch.setattr(settings, "constrained_planning", True)
    captured: dict = {}

    def fake_chat(messages, temperature=0.3, timeout=90, extra=None):
        captured["extra"] = extra
        return CANNED_PLAN_JSON

    monkeypatch.setattr(llm_service, "chat", fake_chat)

    intent = Intent(raw_query="most played artists", plain_restatement="Most played artists")
    plan = SQLGenerator()._constrained_plan(intent, soundwave_profile)

    schema = captured["extra"]["response_format"]["schema"]
    assert schema["properties"]["tables"]["items"]["enum"] == [
        t.name for t in soundwave_profile.tables
    ]
    assert "play_events.artist_id" not in schema["properties"]["output_columns"]["items"]["enum"]

    # Deterministic completion: bridge table + join edges recomputed from the graph
    assert plan is not None
    assert {"artists", "track_artists", "play_events"} <= set(plan["tables"])
    assert len(plan["join_on"]) == 2


def test_generator_uses_locked_plan_in_prompt(
    monkeypatch, soundwave_profile, patched_vector_context
):
    monkeypatch.setattr(settings, "constrained_planning", True)

    def fake_chat(messages, temperature=0.3, timeout=90, extra=None):
        return CANNED_PLAN_JSON

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    captured = _capture_generation(monkeypatch)

    intent = Intent(raw_query="most played artists", plain_restatement="Most played artists")
    candidate = SQLGenerator().generate(intent, soundwave_profile)

    prompt = captured["prompt"]
    assert "Query plan (LOCKED" in prompt
    assert "track_artists" in prompt
    assert "track_artists" in candidate.tables_used


CANNED_PLAN_JSON_MISMATCHED = (
    '{"tables": ["daily_artist_metrics", "play_events"], "join_on": [], '
    '"output_columns": ["artists.name"]}'
)

# The verifier's real rejection for the "most reproduced artists" failure —
# rejected SQL uses aliases (da/pe, no real table names), the legal-chain hint
# names the real tables to route through.
VERIFIER_FEEDBACK = (
    "Rejected SQL:\nSELECT a.name FROM daily_artist_metrics da "
    "JOIN play_events pe ON da.artist_id = pe.track_id;\n"
    "Reason: Invented join key: 'da.artist_id = pe.track_id' is not a relationship "
    "in the schema. The legal join chain from daily_artist_metrics to play_events "
    "is: daily_artist_metrics.artist_id = track_artists.artist_id ; "
    "play_events.track_id = track_artists.track_id — join through the "
    "intermediate table(s), copying these ON clauses verbatim."
)


def test_tables_in_feedback_extracts_real_tables_only(soundwave_profile):
    """Aliases from the rejected SQL (da, pe) must drop out; the legal-chain
    tables must all be captured."""
    assert _tables_in_feedback(VERIFIER_FEEDBACK, soundwave_profile) == {
        "daily_artist_metrics",
        "track_artists",
        "play_events",
    }


def test_plan_pulls_in_output_column_owner_tables(monkeypatch, soundwave_profile):
    """Fix for the "most reproduced artists" failure: the planner picked
    daily_artist_metrics + play_events but offered artists.name as an output
    column — the prompt then said "use ONLY these tables" while requiring a
    column from a table outside them, and the model resolved the contradiction
    by hallucinating the phantom alias `a`. The owner table must be folded in
    and the join tree recomputed over the reconciled set."""
    monkeypatch.setattr(settings, "constrained_planning", True)
    monkeypatch.setattr(llm_service, "chat", lambda *a, **k: CANNED_PLAN_JSON_MISMATCHED)

    intent = Intent(
        raw_query="who are the most reproduced artists of the last year?",
        plain_restatement="Most reproduced artists in the last year",
    )
    plan = SQLGenerator()._constrained_plan(intent, soundwave_profile)

    assert plan is not None
    owners = {c.split(".", 1)[0] for c in plan["output_columns"]}
    assert owners <= set(plan["tables"])  # no output column without its table
    assert "artists" in plan["tables"]
    assert "track_artists" in plan["tables"]  # bridge recomputed over the union
    assert any("track_artists" in edge for edge in plan["join_on"])


def test_regeneration_replans_with_verifier_feedback(
    monkeypatch, soundwave_profile, patched_vector_context
):
    """A regeneration pass must NOT reuse attempt 1's plan (it locked the very
    tables the verifier rejected): the plan step runs again, sees the
    rejection, and its legal-chain tables are folded into the new plan."""
    monkeypatch.setattr(settings, "constrained_planning", True)
    plan_prompts: list[str] = []

    def fake_chat(messages, temperature=0.3, timeout=90, extra=None):
        # Two constrained-decoding steps now share llm_service.chat — planning
        # and structured emission — so this counts plan calls by their system
        # prompt rather than assuming every grammar call is a plan.
        if messages[0]["content"] is PLAN_SYSTEM_PROMPT:
            plan_prompts.append(messages[-1]["content"])
        return CANNED_PLAN_JSON_MISMATCHED

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    captured = _capture_generation(monkeypatch)

    intent = Intent(
        raw_query="who are the most reproduced artists of the last year?",
        plain_restatement="Most reproduced artists in the last year",
    )
    gen = SQLGenerator()
    gen.generate(intent, soundwave_profile)
    gen.generate(intent, soundwave_profile, feedback=VERIFIER_FEEDBACK)

    assert len(plan_prompts) == 2  # replanned, not reused
    assert "Rejected SQL" in plan_prompts[1]  # planner saw the rejection
    # The regeneration prompt's locked plan routes through the legal chain
    assert "Query plan (LOCKED" in captured["prompt"]
    assert "track_artists" in captured["prompt"]


def test_plan_failure_degrades_gracefully(monkeypatch, soundwave_profile, patched_vector_context):
    """An older llama.cpp (no json_schema support) or a timeout must never
    break generation — the plan is an upgrade, not a dependency."""
    monkeypatch.setattr(settings, "constrained_planning", True)

    def failing_chat(messages, temperature=0.3, timeout=90, extra=None):
        raise ConnectionError("no grammar support")

    monkeypatch.setattr(llm_service, "chat", failing_chat)
    captured = _capture_generation(monkeypatch)

    intent = Intent(raw_query="most played artists", plain_restatement="Most played artists")
    candidate = SQLGenerator().generate(intent, soundwave_profile)
    assert candidate.sql  # generation still produced SQL
    assert "Query plan (LOCKED" not in captured["prompt"]
