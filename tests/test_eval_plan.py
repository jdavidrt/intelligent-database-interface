"""Pins the run planner: which items a preset selects, and why that is not a choice.

Offline — reads the four frozen manifests, no backend, no LLM, no model.

EVALUATION_PROTOCOL.md §0 exists to stop a favourable subset being chosen after
the scores are in. The planner is the component that could quietly do exactly
that, so what these tests really assert is the *absence* of freedom: given a
preset, the selected items are a pure function of the manifests, reproducible,
and a strict manifest-order prefix of each stratum. The 30-minute preset is
allowed to be easy-weighted — that is the point of a smoke run — but it must
then say so in the caveats, because an easy-weighted EX is an inflated EX.
"""

from __future__ import annotations

import pytest

from evaluation.corpus import CORPUS_SIZES, load_corpus
from evaluation.plan import (
    EASY_WEIGHTED_SHARES,
    PROFILES,
    TIER_AXIS,
    TIERS,
    TOTAL_ITEMS,
    format_duration,
    plan_run,
    selection_caveats,
    tier_of,
)

ALL_CORPORA = list(CORPUS_SIZES)


@pytest.fixture(scope="module")
def manifests() -> dict[str, list]:
    return {name: load_corpus(name) for name in ALL_CORPORA}


# -- sizes ---------------------------------------------------------------------


@pytest.mark.parametrize("key", list(PROFILES))
def test_each_preset_selects_exactly_its_declared_size(key: str) -> None:
    """A preset that quietly resized itself would make two runs of the same
    name incomparable — the whole reason the budgets are item counts."""
    items, selection = plan_run(key)
    assert len(items) == PROFILES[key].size
    assert selection["selected"] == PROFILES[key].size


def test_full_preset_is_the_whole_corpus_and_not_a_subset() -> None:
    items, selection = plan_run("full")
    assert len(items) == TOTAL_ITEMS == 225
    assert selection["subset"] is False
    assert {item.id for item in items} == {
        item.id for name in ALL_CORPORA for item in load_corpus(name)
    }


def test_presets_are_strictly_increasing_in_size() -> None:
    sizes = [PROFILES[key].size for key in ("30m", "1h", "3h", "full")]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == len(sizes)


# -- determinism and the absence of choice -------------------------------------


@pytest.mark.parametrize("key", list(PROFILES))
def test_plan_is_reproducible(key: str) -> None:
    first, _ = plan_run(key)
    second, _ = plan_run(key)
    assert [item.id for item in first] == [item.id for item in second]


@pytest.mark.parametrize("key", list(PROFILES))
def test_selection_never_duplicates_an_item(key: str) -> None:
    items, _ = plan_run(key)
    ids = [item.id for item in items]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("key", list(PROFILES))
def test_every_stratum_is_a_manifest_order_prefix(key: str, manifests) -> None:
    """The load-bearing invariant.

    The planner may decide *how many* easy spider items run; it may not decide
    *which*. Taking the first N of each (corpus, tier, behaviour) stratum in
    authored order is what makes that true, and this test is what stops a
    future 'let's pick the interesting ones' refactor.
    """
    items, _ = plan_run(key)
    selected_by_corpus: dict[str, set[str]] = {}
    for item in items:
        selected_by_corpus.setdefault(item.corpus, set()).add(item.id)

    for corpus, chosen in selected_by_corpus.items():
        strata: dict[tuple[str, str], list] = {}
        for item in manifests[corpus]:
            behaviour = "answer" if item.expected_behaviour == "answer" else "behaviour"
            key_ = (behaviour, tier_of(item) if behaviour == "answer" else "-")
            strata.setdefault(key_, []).append(item)

        for stratum in strata.values():
            taken = [item.id in chosen for item in stratum]
            # A prefix is exactly: no selected item after an unselected one.
            assert taken == sorted(taken, reverse=True), (
                f"{corpus}: selection is not a manifest-order prefix of its stratum — "
                f"{[i.id for i in stratum]} -> {taken}"
            )


# -- difficulty weighting ------------------------------------------------------


def test_30m_is_easy_weighted() -> None:
    _, selection = plan_run("30m")
    totals = selection["tier_totals"]
    assert selection["tier_rule"] == "easy_weighted"
    # `medium >= hard` rather than a strict chain: at a 20-item budget split
    # four ways, the 30/20 halves of the target round to the same integer.
    # The skew that matters is asserted against the proportional rule below.
    assert totals["easy"] > totals["medium"] >= totals["hard"]
    # Within a couple of items of the 50/30/20 target, after integer rounding
    # and the slot conceded to the clarify stratum.
    for tier, share in EASY_WEIGHTED_SHARES.items():
        assert abs(totals[tier] - share * selection["selected"]) <= 2.5


def test_30m_has_strictly_more_easy_items_than_the_proportional_rule() -> None:
    """The comparison that actually defines 'easy-weighted'.

    Asserting a 50/30/20 histogram alone would still pass if the authored
    corpora happened to be 50/30/20 already. What must hold is that the smoke
    preset skews *relative to* the protocol mix at the same budget.
    """
    _, easy = plan_run(PROFILES["30m"])
    proportional = PROFILES["1h"].__class__("cmp", "cmp", PROFILES["30m"].size, "proportional")
    _, mixed = plan_run(proportional)
    assert easy["selected"] == mixed["selected"]
    assert easy["tier_totals"]["easy"] > mixed["tier_totals"]["easy"]
    assert easy["tier_totals"]["hard"] < mixed["tier_totals"]["hard"]


@pytest.mark.parametrize("key", ["1h", "3h"])
def test_pilot_presets_track_the_authored_stratification(key: str, manifests) -> None:
    """1h and 3h must not skew: their tier mix approximates the full corpus."""
    _, subset = plan_run(key)
    _, whole = plan_run("full")
    scale = subset["selected"] / whole["selected"]
    for tier in TIERS:
        expected = whole["tier_totals"][tier] * scale
        assert (
            abs(subset["tier_totals"][tier] - expected) <= 4
        ), f"{key}: {tier} tier is {subset['tier_totals'][tier]}, expected ~{expected:.1f}"


def test_corpora_are_represented_proportionally() -> None:
    _, selection = plan_run("1h")
    for name, count in selection["per_corpus"].items():
        expected = CORPUS_SIZES[name] * selection["selected"] / TOTAL_ITEMS
        assert abs(count - expected) <= 1


# -- §3.6 behaviour items ------------------------------------------------------


@pytest.mark.parametrize("key", list(PROFILES))
def test_every_preset_exercises_the_clarify_path(key: str) -> None:
    """§3.6's five Deliberate Ambiguity items sit at the tail of the exec
    manifest, so a plain tier-prefix left the clarify path untested even at 190
    of 225 items. They are stratified separately for exactly this reason."""
    _, selection = plan_run(key)
    assert selection["expected_behaviour_counts"].get("clarify", 0) >= 1


# -- caveats -------------------------------------------------------------------


def test_easy_weighted_run_declares_its_inflation() -> None:
    _, selection = plan_run("30m")
    caveats = selection_caveats(selection)
    assert any("easy-weighted" in caveat and "inflated" in caveat for caveat in caveats)


def test_full_run_carries_no_selection_caveat() -> None:
    _, selection = plan_run("full")
    assert selection_caveats(selection) == []


def test_dropped_behaviour_is_reported_but_an_absent_one_is_not() -> None:
    """A caveat about `block` items is about the corpus, not the selection —
    the corpora hold none — so it must not fire. A dropped `clarify` must."""
    dropped = {
        "tier_rule": "proportional",
        "tier_totals": dict.fromkeys(TIERS, 1),
        "expected_behaviour_counts": {"answer": 10},
        "available_behaviour_counts": {"answer": 220, "clarify": 5},
        "subset": True,
    }
    assert any("clarify" in caveat for caveat in selection_caveats(dropped))

    absent = {**dropped, "available_behaviour_counts": {"answer": 220}}
    assert selection_caveats(absent) == []


# -- the normalized axis -------------------------------------------------------


def test_tier_axis_covers_every_difficulty_label_in_every_manifest(manifests) -> None:
    """Guards a future corpus edit that introduces an unmapped tier: the
    planner would otherwise silently mis-bin it or crash mid-run."""
    for name, items in manifests.items():
        for item in items:
            assert item.difficulty in TIER_AXIS[name], (
                f"{item.id}: difficulty {item.difficulty!r} is not mapped in "
                f"TIER_AXIS[{name!r}]"
            )


def test_tier_axis_has_no_stale_corpora_or_targets() -> None:
    assert set(TIER_AXIS) == set(CORPUS_SIZES)
    assert all(target in TIERS for mapping in TIER_AXIS.values() for target in mapping.values())


def test_normalized_tiers_never_reach_the_report(manifests) -> None:
    """Reports break EX down by the native label (`aggregate` reads
    `item.difficulty`), so the allocation axis must stay internal."""
    items, _ = plan_run("30m")
    native = {item.difficulty for item in items}
    assert native - set(TIERS), "expected native labels such as 'simple'/'low', not the axis"


# -- display helpers -----------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [(60, "~1m"), (1800, "~30m"), (3600, "~1h 00m"), (12375, "~3h 26m")],
)
def test_format_duration(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected
