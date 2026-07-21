"""The "Possibly right" verdict — things the schema cannot decide.

Some queries are neither right nor wrong until you know what the user meant:

- **Ambiguous join route (0c).** playlists->tracks is two hops through a
  junction table via `playlist_tracks` ("tracks IN the playlist"), `play_events`
  ("tracks PLAYED FROM it") or `user_liked_tracks`. All three are equally short
  and equally legal; `_score`'s lexicographic tiebreak picks one by accident of
  spelling. There is no faithful truth to recover here — the question decides,
  and the FK graph never sees the question.
- **Self-join direction.** `genres child JOIN genres parent` — the graph knows
  tables, not roles, so it cannot tell parent-of from child-of. Swapping the two
  columns yields equally legal SQL answering the opposite question.
- **Unresolvable join side.** A subquery, CTE or outer-scope alias has no schema
  table behind it, so rule 4b has nothing to check against.
- **Extra key-column equality.** The join is anchored on a real FK, but carries
  a second equality between two unrelated *key* columns.

Passing these silently claims a certainty the system does not have; rejecting
them throws away correct SQL. Both are lies. `verdict == "caution"` says the
true thing — the query ran, and here is the reading it assumed — and the caveat
rides into the didactic answer, which is the whole point of a teaching tool.

Invariant across this whole file: **a caveat never blocks execution.**
`overall_passed` stays True and the SQL really runs.
"""

from __future__ import annotations

import pytest

from backend.app.agents.verification import VerificationAgent
from backend.app.models.envelope import SqlCandidate
from backend.app.services.db.join_graph import JoinGraph


@pytest.fixture(scope="module")
def verifier(soundwave_connector) -> VerificationAgent:
    return VerificationAgent(soundwave_connector)


def _verify(verifier, profile, sql: str):
    return verifier.verify(SqlCandidate(sql=sql.strip()), profile)


# -- 0c: ambiguous junction bridge ---------------------------------------------------


def test_ambiguous_bridges_lists_the_tied_routes(soundwave_profile):
    graph = JoinGraph(soundwave_profile.relationship_edges)
    routes = graph.ambiguous_bridges("playlists", "tracks")
    assert ("playlist_tracks",) in routes and ("play_events",) in routes
    # An unambiguous pair returns nothing at all.
    assert graph.ambiguous_bridges("artists", "genres") == []
    assert graph.ambiguous_bridges("artists", "albums") == []


def test_ambiguous_route_is_caution_not_failure(verifier, soundwave_profile):
    """0c, the case with no faithful answer: 'tracks played from playlist X'
    and 'tracks in playlist X' are both legal readings of the same question."""
    report = _verify(
        verifier,
        soundwave_profile,
        """
        SELECT t.title FROM playlists pl
        JOIN play_events pe ON pe.playlist_id = pl.playlist_id
        JOIN tracks t ON t.track_id = pe.track_id
        LIMIT 5;
        """,
    )
    assert report.overall_passed, "an ambiguous route must never block execution"
    assert report.verdict == "caution"
    assert any("Ambiguous join route" in c for c in report.caveats)
    # The caveat has to name the alternative, or it teaches nothing.
    assert any("playlist_tracks" in c for c in report.caveats)


def test_unambiguous_route_stays_a_clean_pass(verifier, soundwave_profile):
    report = _verify(
        verifier,
        soundwave_profile,
        "SELECT a.name, al.title FROM artists a "
        "JOIN albums al ON al.artist_id = a.artist_id LIMIT 5;",
    )
    assert report.verdict == "pass"
    assert report.caveats == []


def test_production_profile_carries_the_survey_preferences(soundwave_profile):
    """The fixture mirrors ContextManager, which is what the app builds — if it
    ever drifts back to bare introspect(), survey-driven behaviour would look
    broken here while working in the app (and vice versa).

    Also pins that `_comment` keys stay out: JSON has no comments, so survey
    files document themselves with a `"_comment"` entry, which must never reach
    the model as a real glossary term or join preference."""
    assert soundwave_profile.join_preferences.get("artists|play_events") == "track_artists"
    assert soundwave_profile.glossary, "survey glossary not applied to the profile"
    for mapping in (
        soundwave_profile.glossary,
        soundwave_profile.coded_value_maps,
        soundwave_profile.source_of_truth,
        soundwave_profile.join_preferences,
    ):
        assert not any(k.startswith("_") for k in mapping), f"comment key leaked: {mapping}"


def test_survey_preference_settles_a_tie(verifier, soundwave_profile):
    """A human can settle what the schema cannot. `join_preferences` in the
    per-DB survey declares the canonical bridge; EC-08 documents `track_artists`
    for artists<->play_events, so that route stops nagging — while the *other*
    route for the same pair still earns a caveat, which is the point."""
    profile = soundwave_profile.model_copy(deep=True)
    profile.join_preferences = {"artists|play_events": "track_artists"}
    canonical = _verify(
        verifier,
        profile,
        "SELECT a.name FROM artists a "
        "JOIN track_artists ta ON ta.artist_id = a.artist_id "
        "JOIN play_events pe ON pe.track_id = ta.track_id LIMIT 5;",
    )
    assert canonical.verdict == "pass", canonical.caveats

    other = _verify(
        verifier,
        profile,
        "SELECT a.name FROM artists a "
        "JOIN user_follows_artists u ON u.artist_id = a.artist_id "
        "JOIN play_events pe ON pe.user_id = u.user_id LIMIT 5;",
    )
    assert other.verdict == "caution"
    assert any("track_artists" in c for c in other.caveats)


def test_without_a_preference_the_pair_stays_ambiguous(verifier, soundwave_profile):
    """The honest default: absent a declaration, the tie is reported, not hidden."""
    profile = soundwave_profile.model_copy(deep=True)
    profile.join_preferences = {}
    report = _verify(
        verifier,
        profile,
        "SELECT a.name FROM artists a "
        "JOIN track_artists ta ON ta.artist_id = a.artist_id "
        "JOIN play_events pe ON pe.track_id = ta.track_id LIMIT 5;",
    )
    assert report.verdict == "caution"


# -- self-joins: rule 4b cannot judge roles ------------------------------------------


def test_self_join_is_caution_with_a_direction_warning(verifier, soundwave_profile):
    """Previously a silent skip: rule 4b bailed on l_table == r_table and said
    nothing, so an inverted parent/child join passed as fully verified."""
    report = _verify(
        verifier,
        soundwave_profile,
        "SELECT child.name FROM genres child "
        "JOIN genres parent ON child.parent_genre_id = parent.genre_id LIMIT 5;",
    )
    assert report.overall_passed
    assert report.verdict == "caution"
    assert any("Unverified self-join" in c and "genres" in c for c in report.caveats)
    assert any("direction" in c for c in report.caveats)


def test_inverted_self_join_also_only_cautions(verifier, soundwave_profile):
    """The reverse direction is equally legal SQL — the schema cannot rank them,
    so it must not pretend to. Both get the same caveat."""
    report = _verify(
        verifier,
        soundwave_profile,
        "SELECT g1.name FROM genres g1 JOIN genres g2 ON g1.genre_id = g2.parent_genre_id LIMIT 5;",
    )
    assert report.overall_passed and report.verdict == "caution"


# -- unresolvable join sides ----------------------------------------------------------


def test_cte_join_key_is_flagged_as_unverified(verifier, soundwave_profile):
    """The CTE is legal (that was 0e) but its join key genuinely cannot be
    checked against the foreign keys — 'top' is not a schema table."""
    report = _verify(
        verifier,
        soundwave_profile,
        """
        WITH top AS (SELECT ta.artist_id FROM track_artists ta)
        SELECT a.name FROM artists a JOIN top ON top.artist_id = a.artist_id LIMIT 5;
        """,
    )
    assert report.overall_passed and report.verdict == "caution"
    assert any("Unverified join condition" in c and "top" in c for c in report.caveats)


# -- extra key-column equality --------------------------------------------------------


def test_bogus_extra_key_equality_is_flagged(verifier, soundwave_profile):
    """Anchored on a real FK, so it is not rejected — but the second equality
    compares two unrelated key columns, which is not a plausible filter."""
    report = _verify(
        verifier,
        soundwave_profile,
        "SELECT a.name FROM artists a "
        "JOIN albums al ON al.artist_id = a.artist_id AND al.album_id = a.artist_id LIMIT 5;",
    )
    assert report.overall_passed and report.verdict == "caution"
    assert any("Unverified extra join condition" in c for c in report.caveats)


def test_ordinary_filter_in_on_stays_a_clean_pass(verifier, soundwave_profile):
    """The discriminator: `label`/`release_date` are not key columns, so these
    are ordinary filters and must NOT produce a caveat. Without this, the whole
    false-positive fix in 0g would come back as caveat noise instead."""
    for sql in (
        "SELECT a.name, al.title FROM artists a "
        "JOIN albums al ON al.artist_id = a.artist_id AND al.label = a.label LIMIT 5;",
        "SELECT t.title FROM tracks t "
        "JOIN albums al ON al.album_id = t.album_id "
        "AND al.release_date = t.release_date LIMIT 5;",
    ):
        report = _verify(verifier, soundwave_profile, sql)
        assert report.verdict == "pass", report.caveats


# -- the invariant --------------------------------------------------------------------


CAUTION_SQL = [
    "SELECT child.name FROM genres child "
    "JOIN genres parent ON child.parent_genre_id = parent.genre_id LIMIT 5;",
    "SELECT t.title FROM playlists pl JOIN play_events pe ON pe.playlist_id = pl.playlist_id "
    "JOIN tracks t ON t.track_id = pe.track_id LIMIT 5;",
    "WITH top AS (SELECT ta.artist_id FROM track_artists ta) "
    "SELECT a.name FROM artists a JOIN top ON top.artist_id = a.artist_id LIMIT 5;",
    "SELECT a.name FROM artists a "
    "JOIN albums al ON al.artist_id = a.artist_id AND al.album_id = a.artist_id LIMIT 5;",
]


@pytest.mark.parametrize("sql", CAUTION_SQL)
def test_caveats_never_block_execution(verifier, soundwave_profile, soundwave_connector, sql):
    """The load-bearing promise of the third verdict. If a caveat ever blocked,
    it would just be a rejection wearing a friendlier word."""
    report = _verify(verifier, soundwave_profile, sql)
    assert report.overall_passed
    assert report.caveats, "expected this shape to carry a caveat"
    assert report.repaired_sql is None, "a caveat must not trigger the repair path"
    soundwave_connector.execute_read(sql)  # and it really runs


def test_a_failure_is_still_a_failure_not_a_caveat(verifier, soundwave_profile):
    """Ambiguity is not an excuse: an invented join key stays a hard rejection,
    and 'fail' outranks any caveat collected on the way."""
    report = _verify(
        verifier,
        soundwave_profile,
        "SELECT a.name FROM artists a JOIN play_events pe ON a.artist_id = pe.user_id LIMIT 5;",
    )
    assert not report.overall_passed
    assert report.verdict == "fail"
    assert "Invented join key" in report.semantic.message
