"""Run planning — which corpus items a sweep executes, decided before it starts.

EVALUATION_PROTOCOL.md gives the harness no freedom over *which* items get
reported: §0 exists to stop a favourable subset being chosen after the scores
are in. Everything in this module is therefore a pure function of the manifests
and the requested budget, computed before the first HTTP request leaves the
process and recorded verbatim in the run header.

The four presets are wall-clock *labels* over fixed item counts. The counts do
not float with measured latency — a preset that silently changed size between
runs would make two "1 hour runs" incomparable. `estimate_seconds()` converts a
count to a duration for display only.

The 30-minute preset deliberately over-weights easy items, which inflates EX.
That is a legitimate smoke test and an illegitimate result, so
`selection_caveats()` says so in the report and `build_header` marks any subset
run unreportable.
"""

from __future__ import annotations

from typing import Any

from evaluation.corpus import CORPUS_SIZES, CorpusItem, load_corpus

# -- the normalized difficulty axis -------------------------------------------
#
# ALLOCATION ONLY. The four corpora speak four tier vocabularies (§2.1), and
# splitting a budget across them needs one axis. This mapping is never used for
# scoring or reporting: `run.aggregate()` breaks EX down by `item.difficulty`,
# the native label, so the normalized tier never reaches a published table.
#
# It is deliberately NOT derived by inverting hardness.py's BIRD_FROM_SPIDER /
# EXEC_FROM_SPIDER. Those are many-to-one (Spider `easy` and `medium` both map
# to BIRD `simple`), so no inverse exists and pretending one does would silently
# mis-bin half of bird_style.
TIER_AXIS: dict[str, dict[str, str]] = {
    "spider_style": {"easy": "easy", "medium": "medium", "hard": "hard", "extra": "hard"},
    "bird_style": {"simple": "easy", "moderate": "medium", "challenging": "hard"},
    "soundwave_30": {
        "Easy": "easy",
        "Medium": "medium",
        "Hard": "hard",
        "Extra Hard": "hard",
    },
    "idi_exec_75": {"low": "easy", "medium": "medium", "high": "hard"},
}

TIERS = ("easy", "medium", "hard")

# §2.1's easy-weighted target for the smoke preset. Clipped to availability.
EASY_WEIGHTED_SHARES = {"easy": 0.50, "medium": 0.30, "hard": 0.20}

# End-to-end p50 of the 26-item pilot of 2026-07-21 (greedy, frozen clock, GPU
# profile): 87.6s. Used to size the presets below, and to label them when no
# newer report is on disk. The 2026-07-14 run implied ~55s by summing stage
# means, which understated it — stages overlap with orchestration overhead the
# stage sum does not see.
FALLBACK_SECONDS_PER_ITEM = 87.6

TOTAL_ITEMS = sum(CORPUS_SIZES.values())


class Profile:
    """One menu preset: a fixed item count and a tier rule."""

    def __init__(self, key: str, label: str, items: int | None, tier_rule: str, note: str = ""):
        self.key = key
        self.label = label
        # None means "every item"; kept distinct from TOTAL_ITEMS so the full
        # run is never described as a subset.
        self.items = items
        self.tier_rule = tier_rule
        self.note = note

    @property
    def size(self) -> int:
        return TOTAL_ITEMS if self.items is None else self.items


# Item counts, sized once against FALLBACK_SECONDS_PER_ITEM. They are constants,
# not a function of the latest measurement: a preset that resized itself between
# runs would make two runs of the same name incomparable. If the pipeline gets
# materially faster, these are re-derived deliberately and the change recorded —
# the menu meanwhile shows the honest estimate from the newest report.
PROFILES: dict[str, Profile] = {
    "30m": Profile(
        "30m",
        "30 minutes",
        20,
        "easy_weighted",
        "smoke run — over-weights easy items, so its EX is inflated by construction",
    ),
    "1h": Profile("1h", "1 hour", 41, "proportional", "pilot run — authored tier mix"),
    "3h": Profile("3h", "3 hours", 123, "proportional", "pilot run — authored tier mix"),
    "full": Profile(
        "full",
        "full run",
        None,
        "all",
        "the only reportable option — all 225 items, §3 corpus EX",
    ),
}


def tier_of(item: CorpusItem) -> str:
    """Normalized allocation tier for one item. Raises on an unmapped label."""
    mapping = TIER_AXIS[item.corpus]
    if item.difficulty not in mapping:
        raise KeyError(
            f"{item.id}: difficulty {item.difficulty!r} is not in TIER_AXIS[{item.corpus!r}]. "
            f"A corpus gained a tier label the planner cannot allocate — extend TIER_AXIS."
        )
    return mapping[item.difficulty]


# -- allocation ----------------------------------------------------------------


def _largest_remainder(
    weights: dict[str, float], total: int, caps: dict[str, int]
) -> dict[str, int]:
    """Apportion `total` across `weights`, capped by `caps`, deterministically.

    Standard largest-remainder rounding. Ties break on the insertion order of
    `weights`, which callers fix, so the same inputs always give the same
    allocation — there is no seed and no dict-ordering dependence.
    """
    pool = sum(weights.values())
    if pool <= 0 or total <= 0:
        return {key: 0 for key in weights}

    exact = {key: total * weight / pool for key, weight in weights.items()}
    allocated = {key: min(caps[key], int(value)) for key, value in exact.items()}

    order = sorted(
        weights,
        key=lambda key: (-(exact[key] - int(exact[key])), list(weights).index(key)),
    )
    # Repeat until no progress: a key hitting its cap frees units for the rest.
    while sum(allocated.values()) < total:
        progressed = False
        for key in order:
            if sum(allocated.values()) >= total:
                break
            if allocated[key] < caps[key]:
                allocated[key] += 1
                progressed = True
        if not progressed:
            break
    return allocated


def _tier_groups(items: list[CorpusItem]) -> dict[str, list[CorpusItem]]:
    """Manifest order preserved inside each tier — that is the whole point."""
    groups: dict[str, list[CorpusItem]] = {tier: [] for tier in TIERS}
    for item in items:
        groups[tier_of(item)].append(item)
    return groups


def _tier_allocation(groups: dict[str, list[CorpusItem]], budget: int, rule: str) -> dict[str, int]:
    caps = {tier: len(group) for tier, group in groups.items()}
    if rule == "all" or budget >= sum(caps.values()):
        return caps
    if rule == "easy_weighted":
        weights = {tier: EASY_WEIGHTED_SHARES[tier] for tier in TIERS}
    else:  # "proportional" — the corpus's own authored histogram
        weights = {tier: float(caps[tier]) for tier in TIERS}
    return _largest_remainder(weights, budget, caps)


def plan_run(
    profile: str | Profile, corpora: list[str] | None = None
) -> tuple[list[CorpusItem], dict[str, Any]]:
    """Select the items for one preset. Deterministic, offline, result-blind.

    Three layers, each of which removes freedom rather than adding it:

    1. across corpora — proportional to corpus size;
    2. across tiers within a corpus — the corpus's own histogram, or the
       easy-weighted shares for the smoke preset;
    3. within a tier — a manifest-order prefix. There is no choice of *which*
       easy item runs, only of how many.
    """
    prof = profile if isinstance(profile, Profile) else PROFILES[profile]
    names = corpora or list(CORPUS_SIZES)
    loaded = {name: load_corpus(name) for name in names}
    available = sum(len(rows) for rows in loaded.values())
    budget = available if prof.items is None else min(prof.items, available)

    corpus_weights = {name: float(len(loaded[name])) for name in names}
    corpus_caps = {name: len(loaded[name]) for name in names}
    per_corpus = _largest_remainder(corpus_weights, budget, corpus_caps)

    items: list[CorpusItem] = []
    per_corpus_tier: dict[str, dict[str, int]] = {}
    for name in names:
        # `clarify` / `block` items are stratified separately from `answer`
        # ones. They are scored on pipeline behaviour rather than on a result
        # set (§3.6), and in idi_exec_75 all five sit at the tail of the
        # manifest — so a plain tier-prefix left §3.6 unexercised even at 190
        # of 225 items. Splitting the budget in proportion keeps a share of
        # them in every preset without choosing which ones.
        behaviour_items = [i for i in loaded[name] if i.expected_behaviour != "answer"]
        answer_items = [i for i in loaded[name] if i.expected_behaviour == "answer"]
        split = _largest_remainder(
            {"behaviour": float(len(behaviour_items)), "answer": float(len(answer_items))},
            per_corpus[name],
            {"behaviour": len(behaviour_items), "answer": len(answer_items)},
        )
        # Floor of one. Proportionally the smoke preset earns 0.47 of a clarify
        # item and would round to none, leaving §3.6's behaviour scoring — a
        # separate code path from result comparison, not a harder version of it
        # — untested by the run whose whole job is to catch a broken pipeline.
        # It costs one answer item and is applied identically to every preset.
        if behaviour_items and not split["behaviour"] and split["answer"] > 0:
            split["behaviour"], split["answer"] = 1, split["answer"] - 1

        groups = _tier_groups(answer_items)
        allocation = _tier_allocation(groups, split["answer"], prof.tier_rule)
        per_corpus_tier[name] = allocation
        for tier in TIERS:
            items.extend(groups[tier][: allocation[tier]])
        items.extend(behaviour_items[: split["behaviour"]])

    behaviours: dict[str, int] = {}
    tier_totals: dict[str, int] = {tier: 0 for tier in TIERS}
    for item in items:
        behaviours[item.expected_behaviour] = behaviours.get(item.expected_behaviour, 0) + 1
        tier_totals[tier_of(item)] += 1

    available_behaviours: dict[str, int] = {}
    for rows in loaded.values():
        for item in rows:
            available_behaviours[item.expected_behaviour] = (
                available_behaviours.get(item.expected_behaviour, 0) + 1
            )

    selection: dict[str, Any] = {
        "profile": prof.key,
        "profile_label": prof.label,
        "tier_rule": prof.tier_rule,
        # No item count here: the report and the banner both append their own.
        "rule": (
            f"{prof.label} preset — proportional across corpora, {prof.tier_rule} across "
            f"difficulty tiers, manifest-order prefix within each stratum"
        ),
        "per_corpus": {name: per_corpus[name] for name in names},
        "per_corpus_tier": per_corpus_tier,
        "tier_totals": tier_totals,
        "expected_behaviour_counts": behaviours,
        "available_behaviour_counts": available_behaviours,
        "selected": len(items),
        "available": {name: len(rows) for name, rows in loaded.items()},
        "subset": len(items) < available,
        "tier_axis": "normalized for allocation only; reports use native tier labels",
    }
    return items, selection


def selection_caveats(selection: dict[str, Any]) -> list[str]:
    """Everything about this selection that would mislead a reader of the EX."""
    caveats: list[str] = []
    if selection.get("tier_rule") == "easy_weighted":
        shares = ", ".join(f"{tier} {selection['tier_totals'][tier]}" for tier in TIERS)
        caveats.append(
            f"easy-weighted subset ({shares}): EX is inflated relative to the authored "
            f"stratification of §2.1 and is not comparable with a protocol-mix run"
        )
    # Only a *dropped* behaviour is worth reporting. The corpora currently hold
    # no `block` items at all, so warning about their absence would be noise
    # about the corpus rather than about this selection.
    selected = selection.get("expected_behaviour_counts", {})
    available = selection.get("available_behaviour_counts", {})
    dropped = [
        kind for kind in ("clarify", "block") if available.get(kind) and not selected.get(kind)
    ]
    if dropped:
        caveats.append(
            f"no {' or '.join(dropped)} items were selected although the corpora contain "
            f"some, so §3.6 behaviour scoring went unexercised in this run"
        )
    return caveats


def estimate_seconds(count: int, seconds_per_item: float | None = None) -> float:
    """Display-only duration estimate. Never feeds back into selection."""
    return count * (seconds_per_item or FALLBACK_SECONDS_PER_ITEM)


def format_duration(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return f"~{minutes}m"
    return f"~{minutes // 60}h {minutes % 60:02d}m"


# -- legacy flag path ----------------------------------------------------------


def select_items(
    corpora: list[str], total: int | None, per_corpus: int | None
) -> tuple[list[CorpusItem], dict]:
    """Deterministic manifest-order prefix, allocated proportionally.

    Backs the older `--total` / `--per-corpus` flags. Unlike `plan_run` it is
    tier-blind: it takes the top N of each manifest whatever their difficulty.
    Kept unchanged so existing invocations reproduce their previous selection.
    """
    loaded = {name: load_corpus(name) for name in corpora}
    if total is None and per_corpus is None:
        chosen = {name: len(items) for name, items in loaded.items()}
        rule = "full corpora"
    elif per_corpus is not None:
        chosen = {name: min(per_corpus, len(items)) for name, items in loaded.items()}
        rule = f"first {per_corpus} items of each corpus, manifest order"
    else:
        pool = sum(len(items) for items in loaded.values())
        chosen = {
            name: min(len(items), max(1, round(total * len(items) / pool)))
            for name, items in loaded.items()
        }
        rule = f"proportional prefix of {total} items across {len(corpora)} corpora, manifest order"

    items: list[CorpusItem] = []
    for name in corpora:
        items.extend(loaded[name][: chosen[name]])

    selection = {
        "rule": rule,
        "per_corpus": chosen,
        "selected": len(items),
        "available": {name: len(rows) for name, rows in loaded.items()},
        "subset": any(chosen[name] < len(loaded[name]) for name in corpora),
    }
    return items, selection
