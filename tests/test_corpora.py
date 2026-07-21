"""Pins the four benchmark corpora to EVALUATION_PROTOCOL.md.

Runs fully offline: the corpora are JSONL on disk and the ground truth comes
from the in-memory FileConnector, so no LLM and no live backend are involved.
That matters because §0.2 makes corpus content near-immutable once a run is
scored — these tests are what make an accidental edit fail loudly instead of
silently changing a published metric.

The heavier conformance logic lives in `evaluation/corpus.py::check_corpus`;
this module asserts it, plus the invariants that are cheap to state directly.
"""

from __future__ import annotations

import os

import pytest

from evaluation.corpus import (
    CORPUS_SIZES,
    EXEC_CATEGORIES,
    EXEC_DIFFICULTY,
    SPIDER_TIERS,
    check_corpus,
    execute,
    load_corpus,
)
from evaluation.hardness import BIRD_FROM_SPIDER, EXEC_FROM_SPIDER, eval_hardness

CORPORA = list(CORPUS_SIZES)


@pytest.mark.parametrize("name", CORPORA)
def test_corpus_is_conformant(name: str) -> None:
    """The single assertion that matters — everything §2.1/§2.2 fixes."""
    problems = check_corpus(name)
    assert not problems, f"{name} violates the protocol:\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("name", CORPORA)
def test_corpus_size_is_frozen(name: str) -> None:
    """§2 sizes may not change (§0.2: 'Add a query to a corpus — No')."""
    assert len(load_corpus(name)) == CORPUS_SIZES[name]


@pytest.mark.parametrize("name", CORPORA)
def test_every_reference_query_executes(name: str) -> None:
    """§3.1 derives ground truth by execution, so a non-executing reference is
    not a weak item — it is an item with no ground truth at all."""
    failures = [
        (item.id, execute(item.reference_sql)[1])
        for item in load_corpus(name)
        if item.expected_behaviour == "answer" and item.reference_sql
        if execute(item.reference_sql)[1]
    ]
    assert not failures, f"{name} reference SQL failed: {failures}"


def test_spider_tier_histogram_is_computed_not_declared() -> None:
    """§2.1: the tier is a property of the SQL. Recomputing it here means a
    later edit to a reference query cannot silently move the distribution."""
    items = load_corpus("spider_style")
    computed: dict[str, int] = {}
    for item in items:
        tier = eval_hardness(item.reference_sql)
        computed[tier] = computed.get(tier, 0) + 1
        assert tier == item.difficulty, f"{item.id}: declared {item.difficulty}, computed {tier}"
    assert computed == SPIDER_TIERS


def test_bird_tier_histogram_and_evidence() -> None:
    items = load_corpus("bird_style")
    computed: dict[str, int] = {}
    for item in items:
        tier = BIRD_FROM_SPIDER[eval_hardness(item.reference_sql)]
        computed[tier] = computed.get(tier, 0) + 1
        assert tier == item.difficulty, f"{item.id}: declared {item.difficulty}, computed {tier}"
        assert item.evidence, f"{item.id}: BIRD items must carry evidence (§2.1)"
    assert computed == {"simple": 30, "moderate": 21, "challenging": 9}


def test_bird_dirty_data_trap_coverage() -> None:
    """§2.1 as amended v1.2: at least 40 of the 60 hit a real SoundWave trap."""
    items = load_corpus("bird_style")
    assert sum(1 for i in items if i.ec_tags) >= 40


def test_exec_category_and_difficulty_distribution() -> None:
    """§2.1 pins both distributions to Chapter 1 §1.5 exactly."""
    items = load_corpus("idi_exec_75")
    categories: dict[str, int] = {}
    difficulties: dict[str, int] = {}
    for item in items:
        categories[item.category] = categories.get(item.category, 0) + 1
        difficulties[item.difficulty] = difficulties.get(item.difficulty, 0) + 1
    assert categories == EXEC_CATEGORIES
    assert difficulties == EXEC_DIFFICULTY


def test_exec_levels_are_computed() -> None:
    for item in load_corpus("idi_exec_75"):
        if item.reference_sql:
            tier = EXEC_FROM_SPIDER[eval_hardness(item.reference_sql)]
            assert tier == item.difficulty, f"{item.id}: declared {item.difficulty}, got {tier}"


def test_clarify_items_carry_no_reference_sql() -> None:
    """§3.6 scores these on behaviour. A reference query on a clarify item is an
    invitation for someone to score it by result comparison later, which would
    mark a correct clarification as a failure."""
    ambiguous = [i for i in load_corpus("idi_exec_75") if i.category == "Deliberate Ambiguity"]
    assert len(ambiguous) == 5
    for item in ambiguous:
        assert item.expected_behaviour == "clarify"
        assert item.reference_sql is None


def test_ec07_items_never_accept_both_sources() -> None:
    """§9 quirk 2 as amended: the pre-aggregated and raw sources differ by ~5
    orders of magnitude, so an item accepting both passes on any answer between
    them. This is the invariant that keeps EC-07 items falsifiable."""
    for name in CORPORA:
        for item in load_corpus(name):
            if "EC-07" in item.ec_tags:
                assert (
                    not item.accepted_alternatives
                ), f"{item.id} accepts alternatives on an EC-07 item — see §9 quirk 2"


def test_soundwave_30_matches_the_edge_case_source() -> None:
    """§2.1 calls this corpus a census. If the syllabus file gains, loses or
    renumbers a query, the manifest is stale and must be regenerated by
    `python -m evaluation.transcribe_soundwave` rather than hand-edited."""
    from evaluation.transcribe_soundwave import SOURCE, build_items, parse_blocks

    with open(SOURCE, encoding="utf-8") as fh:
        regenerated = build_items(parse_blocks(fh.read()))
    on_disk = load_corpus("soundwave_30")

    assert len(regenerated) == 30
    assert [i.id for i in regenerated] == [i.id for i in on_disk]
    for fresh, stored in zip(regenerated, on_disk):
        assert fresh.nl == stored.nl, f"{fresh.id}: NL drifted from the source file"
        assert fresh.reference_sql == stored.reference_sql, f"{fresh.id}: SQL drifted"
        assert fresh.difficulty == stored.difficulty, f"{fresh.id}: tier drifted"
        assert fresh.ec_tags == stored.ec_tags, f"{fresh.id}: EC tags drifted"


def test_ids_are_unique_across_all_corpora() -> None:
    ids = [item.id for name in CORPORA for item in load_corpus(name)]
    assert len(ids) == len(set(ids)) == 225


def test_seed_generator_reproduces_the_data_file_byte_for_byte(tmp_path) -> None:
    """`extend_seed_data.py` must regenerate `02_soundwave_data.sql` exactly.

    This is the deepest assumption in the whole evaluation. §3.1 derives ground
    truth by executing reference SQL against the seeded data rather than storing
    it, precisely so ground truth tracks the data — but that only holds if the
    data itself is reproducible from source. If the generator drifts, all 225
    items silently acquire different correct answers and nothing else in the
    suite notices, because every corpus check would still pass against the new
    data.

    The generator's determinism is a property of RNG *call order*, which makes it
    unusually easy to break by innocent-looking refactors: hoisting an
    `rng.randint` out of an f-string, reordering two draws on one line, or adding
    a draw inside a loop all leave the code reading correctly and rewrite every
    row from that point on. This test is what makes that a red build instead of a
    quiet re-baselining. (Exactly that refactor was done on 2026-07-21 to clear
    three E501s; it passed here, which is the only reason it was kept.)

    Runs on a copy — the script rewrites its data file in place.
    """
    import shutil
    import subprocess
    import sys

    from evaluation.corpus import REPO_ROOT

    source_dir = os.path.join(REPO_ROOT, "databases", "soundwave")
    original = os.path.join(source_dir, "02_soundwave_data.sql")

    work = tmp_path / "soundwave"
    shutil.copytree(source_dir, work)
    script = work / "scripts" / "extend_seed_data.py"
    if not script.exists():  # pragma: no cover - script is optional in a checkout
        pytest.skip("extend_seed_data.py not present")

    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, f"generator failed:\n{result.stderr}"

    with open(original, "rb") as fh:
        expected = fh.read()
    with open(work / "02_soundwave_data.sql", "rb") as fh:
        regenerated = fh.read()

    assert regenerated == expected, (
        "extend_seed_data.py no longer reproduces 02_soundwave_data.sql byte for byte. "
        "Every ground truth in the four corpora is derived by executing reference SQL "
        "against this file, so the corpora are now scoring against data that cannot be "
        "regenerated from source. Check for a changed RNG call order before re-baselining."
    )


# -- The hardness scorer itself ------------------------------------------------
# Three of the four corpora derive their tier from `eval_hardness`, so a silent
# regression here would silently re-stratify 195 items. These pin the binning
# table transcribed from Spider's evaluation.py and the component counts that
# feed it, independently of any corpus.


@pytest.mark.parametrize(
    "sql,expected",
    [
        # easy: comp1 <= 1, others == 0, comp2 == 0
        ("SELECT name FROM artists", "easy"),
        ("SELECT name FROM artists WHERE country = 'CO'", "easy"),
        ("SELECT COUNT(*) FROM tracks WHERE album_id IS NULL", "easy"),
        ("SELECT a.name FROM artists a JOIN albums b ON a.artist_id = b.artist_id", "easy"),
        # medium: a second select column or a second clause tips it over
        ("SELECT title, release_date FROM albums ORDER BY release_date", "medium"),
        ("SELECT title FROM tracks WHERE is_exp = 1 ORDER BY title", "medium"),
        ("SELECT name FROM artists WHERE country = 'CO' OR country = 'US'", "medium"),
        ("SELECT name FROM artists WHERE name LIKE '%a%'", "medium"),
        # hard: a nested query with nothing else, or three component-1 features
        (
            "SELECT name FROM artists WHERE artist_id IN (SELECT artist_id FROM track_artists)",
            "hard",
        ),
        ("SELECT 1 UNION ALL SELECT 2", "hard"),
        ("WITH x AS (SELECT 1 AS a) SELECT a FROM x", "hard"),
        # extra: four component-1 features, or nesting plus clauses
        (
            "SELECT t.title, COUNT(*) FROM tracks t JOIN play_events pe "
            "ON t.track_id = pe.track_id WHERE pe.event_type = 'play' "
            "GROUP BY t.track_id, t.title ORDER BY COUNT(*) DESC",
            "extra",
        ),
        (
            "SELECT title FROM tracks WHERE album_id IN (SELECT album_id FROM albums) "
            "ORDER BY title",
            "extra",
        ),
    ],
)
def test_hardness_binning(sql: str, expected: str) -> None:
    assert eval_hardness(sql) == expected


def test_hardness_counts_are_scope_limited() -> None:
    """Spider counts components on the outermost query only; a nested query is
    one component-2 unit, not a pile of extra component-1 features. If traversal
    leaks into subqueries every tier inflates, which is the failure mode most
    likely to go unnoticed."""
    from evaluation.hardness import components

    shallow = "SELECT name FROM artists WHERE artist_id IN (SELECT artist_id FROM track_artists)"
    deep = (
        "SELECT name FROM artists WHERE artist_id IN "
        "(SELECT artist_id FROM track_artists ta JOIN tracks t ON ta.track_id = t.track_id "
        "WHERE t.is_exp = 1 GROUP BY ta.artist_id ORDER BY ta.artist_id LIMIT 5)"
    )
    # The inner query gained four component-1 features; the outer count must not move.
    assert components(shallow)[0] == components(deep)[0] == 1
    assert components(shallow)[1] == components(deep)[1] == 1


def test_sqlglot_arg_rename_does_not_silently_zero_a_clause() -> None:
    """sqlglot 30 moved FROM to `from_` and WITH to `with_`. Reading the old
    names returns None rather than raising, so a version bump could silently
    stop counting CTEs — which would move `extra` items down to `medium`."""
    from evaluation.hardness import components

    assert components("WITH x AS (SELECT 1 AS a) SELECT a FROM x")[1] == 1
