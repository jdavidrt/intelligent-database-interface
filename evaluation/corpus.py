"""Benchmark corpus manifests: loading, execution and conformance checking.

Implements the manifest schema of EVALUATION_PROTOCOL.md §2.2 and the
structural invariants of §2.1 (fixed sizes, fixed stratification, fixed
category counts). Everything here runs offline against the in-memory
`FileConnector` — no LLM, no live backend — so the corpora stay pinned by the
normal pytest suite rather than only by a manual scored run.

Ground truth is deliberately NOT stored in the manifests. §3.1 requires it to be
"the result set produced by executing `reference_sql` against the seeded
database under the frozen clock", so that it tracks the data if the seed is
ever regenerated. `execute()` below is that definition, in code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

# The frozen clock of §1.1 must be in the environment before anything imports
# services.clock, which reads it at import time. A run without it is void (§1.1),
# so this module refuses to let that happen silently.
FREEZE_NOW = "2026-07-17T12:00:00"
os.environ.setdefault("IDI_FREEZE_NOW", FREEZE_NOW)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA_DIR = os.path.join(REPO_ROOT, "data", "benchmarks", "corpora")

ExpectedBehaviour = Literal["answer", "clarify", "block"]

# -- §2 corpus sizes. Fixed by the protocol; may not change (§0.2). -----------
CORPUS_SIZES = {
    "spider_style": 60,
    "bird_style": 60,
    "soundwave_30": 30,
    "idi_exec_75": 75,
}

# -- §2.1 stratification. Computed tiers must match these exactly. ------------
SPIDER_TIERS = {"easy": 24, "medium": 24, "hard": 9, "extra": 3}
BIRD_TIERS = {"simple": 30, "moderate": 21, "challenging": 9}

# -- §2.1 IDI-EXEC-75 category distribution, from Chapter 1 §1.5. -------------
EXEC_CATEGORIES = {
    "Ranking / Top-N": 10,
    "Aggregations / KPIs": 15,
    "Temporal / Trends": 15,
    "Comparisons": 10,
    "Filtering / Segmentation": 10,
    "Relational / Multi-table": 5,
    "Complex Analysis": 5,
    "Deliberate Ambiguity": 5,
}
EXEC_DIFFICULTY = {"low": 15, "medium": 30, "high": 30}

ID_PREFIXES = {
    "spider_style": "SPIDER",
    "bird_style": "BIRD",
    "soundwave_30": "SW",
    "idi_exec_75": "EXEC",
}


@dataclass
class CorpusItem:
    """One manifest line. Field names and semantics are §2.2."""

    id: str
    corpus: str
    category: str
    difficulty: str
    nl: str
    reference_sql: str | None
    order_matters: bool
    expected_behaviour: ExpectedBehaviour
    ec_tags: list[str] = field(default_factory=list)
    evidence: str | None = None
    accepted_alternatives: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> CorpusItem:
        return cls(
            id=raw["id"],
            corpus=raw["corpus"],
            category=raw["category"],
            difficulty=raw["difficulty"],
            nl=raw["nl"],
            reference_sql=raw.get("reference_sql"),
            order_matters=bool(raw.get("order_matters", False)),
            expected_behaviour=raw.get("expected_behaviour", "answer"),
            ec_tags=list(raw.get("ec_tags") or []),
            evidence=raw.get("evidence"),
            accepted_alternatives=list(raw.get("accepted_alternatives") or []),
            notes=raw.get("notes", "") or "",
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "corpus": self.corpus,
            "category": self.category,
            "difficulty": self.difficulty,
            "nl": self.nl,
            "reference_sql": self.reference_sql,
            "order_matters": self.order_matters,
            "expected_behaviour": self.expected_behaviour,
            "ec_tags": self.ec_tags,
            "evidence": self.evidence,
            "accepted_alternatives": self.accepted_alternatives,
            "notes": self.notes,
        }


def corpus_path(name: str) -> str:
    return os.path.join(CORPORA_DIR, f"{name}.jsonl")


def load_corpus(name: str) -> list[CorpusItem]:
    with open(corpus_path(name), encoding="utf-8") as fh:
        return [CorpusItem.from_json(json.loads(line)) for line in fh if line.strip()]


def write_corpus(name: str, items: list[CorpusItem]) -> None:
    os.makedirs(CORPORA_DIR, exist_ok=True)
    with open(corpus_path(name), "w", encoding="utf-8", newline="\n") as fh:
        for item in items:
            fh.write(json.dumps(item.to_json(), ensure_ascii=False) + "\n")


# -- Execution against the frozen-clock database ------------------------------

_CONNECTOR = None


def connector():
    """The single in-memory SoundWave DB, built once per process."""
    global _CONNECTOR
    if _CONNECTOR is None:
        from backend.app.services.db.file_connector import FileConnector

        _CONNECTOR = FileConnector("soundwave")
        _CONNECTOR.connect()
    return _CONNECTOR


def execute(sql: str) -> tuple[list[tuple], str | None]:
    """Run reference SQL, returning (rows, error).

    Goes through `_mysql_to_sqlite` — the same transpiler the live pipeline uses
    — so a reference query that only works in real MySQL is caught here rather
    than at scoring time.
    """
    from backend.app.services.db.file_connector import _mysql_to_sqlite

    try:
        cursor = connector()._conn.execute(_mysql_to_sqlite(sql))
        return [tuple(row) for row in cursor.fetchall()], None
    except Exception as exc:  # noqa: BLE001 — any failure is a corpus defect
        return [], f"{type(exc).__name__}: {exc}"


# -- Conformance checking -----------------------------------------------------


def check_corpus(name: str) -> list[str]:
    """Return a list of protocol violations. Empty list means conformant."""
    from evaluation.hardness import eval_hardness

    problems: list[str] = []
    items = load_corpus(name)

    expected_size = CORPUS_SIZES[name]
    if len(items) != expected_size:
        problems.append(f"size: expected {expected_size} items (§2), found {len(items)}")

    seen: set[str] = set()
    for item in items:
        where = f"{item.id}"
        if item.id in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(item.id)

        if item.corpus != name:
            problems.append(f"{where}: corpus field is {item.corpus!r}, expected {name!r}")
        if not item.id.startswith(ID_PREFIXES[name]):
            problems.append(f"{where}: id should start with {ID_PREFIXES[name]!r}")
        if item.expected_behaviour not in ("answer", "clarify", "block"):
            problems.append(f"{where}: bad expected_behaviour {item.expected_behaviour!r} (§3.6)")
        if not item.nl.strip():
            problems.append(f"{where}: empty nl")

        # §3.6: only `answer` items are scored by result comparison, so only
        # they require executable reference SQL. clarify/block items are scored
        # on pipeline behaviour and legitimately carry no ground truth.
        if item.expected_behaviour == "answer":
            if not (item.reference_sql or "").strip():
                problems.append(f"{where}: expected_behaviour=answer requires reference_sql")
            else:
                rows, error = execute(item.reference_sql)
                if error:
                    problems.append(f"{where}: reference_sql failed to execute — {error}")
        elif item.reference_sql:
            problems.append(
                f"{where}: expected_behaviour={item.expected_behaviour} must not carry "
                f"reference_sql (§3.6 scores it on behaviour, not results)"
            )

        for alternative in item.accepted_alternatives:
            _, error = execute(alternative)
            if error:
                problems.append(f"{where}: accepted_alternative failed to execute — {error}")

        # Amended §9 quirk 2: pre-aggregated and raw sources differ by ~5 orders
        # of magnitude, so an item that accepts both is unfalsifiable. EC-07
        # items must name their source instead.
        if "EC-07" in item.ec_tags and item.accepted_alternatives:
            problems.append(
                f"{where}: EC-07 item carries accepted_alternatives — the pre-aggregated and "
                f"raw sources differ by ~5 orders of magnitude, so accepting both makes the "
                f"item unfalsifiable (§9 quirk 2, as amended v1.2)"
            )

    problems.extend(_check_stratification(name, items, eval_hardness))
    return problems


def _check_stratification(name, items, eval_hardness) -> list[str]:
    problems: list[str] = []
    scorable = [i for i in items if i.expected_behaviour == "answer" and i.reference_sql]

    if name == "spider_style":
        computed: dict[str, int] = {}
        for item in scorable:
            try:
                tier = eval_hardness(item.reference_sql)
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{item.id}: hardness scoring failed — {exc}")
                continue
            computed[tier] = computed.get(tier, 0) + 1
            if tier != item.difficulty:
                problems.append(
                    f"{item.id}: declared tier {item.difficulty!r} but Spider eval_hardness "
                    f"computes {tier!r} — §2.1 requires re-authoring, not relabelling"
                )
        for tier, want in SPIDER_TIERS.items():
            got = computed.get(tier, 0)
            if got != want:
                problems.append(f"spider tier histogram: {tier} expected {want}, computed {got}")

    if name == "bird_style":
        from evaluation.hardness import BIRD_FROM_SPIDER

        computed: dict[str, int] = {}
        for item in scorable:
            tier = BIRD_FROM_SPIDER[eval_hardness(item.reference_sql)]
            computed[tier] = computed.get(tier, 0) + 1
            if tier != item.difficulty:
                problems.append(
                    f"{item.id}: declared tier {item.difficulty!r} but the computed tier is "
                    f"{tier!r} — §2.1 requires re-authoring, not relabelling"
                )
            if item.evidence is None or not item.evidence.strip():
                problems.append(f"{item.id}: BIRD items must carry an evidence field (§2.1)")
        for tier, want in BIRD_TIERS.items():
            got = computed.get(tier, 0)
            if got != want:
                problems.append(f"bird tier histogram: {tier} expected {want}, computed {got}")
        # §2.1 as amended v1.2: two thirds of the corpus must hit a real trap.
        # The old text said "at least 20 of the 30", left over from when this
        # corpus was 30 items; 40 of 60 preserves the ratio.
        trapped = sum(1 for i in items if i.ec_tags)
        if trapped < 40:
            problems.append(f"bird dirty-data traps: expected >= 40 of 60, got {trapped}")

    if name == "idi_exec_75":
        from evaluation.hardness import EXEC_FROM_SPIDER

        categories: dict[str, int] = {}
        difficulties: dict[str, int] = {}
        for item in items:
            categories[item.category] = categories.get(item.category, 0) + 1
            difficulties[item.difficulty] = difficulties.get(item.difficulty, 0) + 1
            if item.reference_sql:
                tier = EXEC_FROM_SPIDER[eval_hardness(item.reference_sql)]
                if tier != item.difficulty:
                    problems.append(
                        f"{item.id}: declared level {item.difficulty!r} but the computed "
                        f"level is {tier!r} — §2.1 requires re-authoring, not relabelling"
                    )
        for category, want in EXEC_CATEGORIES.items():
            got = categories.get(category, 0)
            if got != want:
                problems.append(f"exec category {category!r}: expected {want}, got {got}")
        for level, want in EXEC_DIFFICULTY.items():
            got = difficulties.get(level, 0)
            if got != want:
                problems.append(f"exec difficulty {level!r}: expected {want}, got {got}")
        ambiguous = [i for i in items if i.category == "Deliberate Ambiguity"]
        for item in ambiguous:
            if item.expected_behaviour != "clarify":
                problems.append(
                    f"{item.id}: Deliberate Ambiguity items must be expected_behaviour="
                    f"clarify (§3.6), got {item.expected_behaviour!r}"
                )

    if name == "soundwave_30":
        expected_ids = {f"SW-Q{n:02d}" for n in range(1, 31)}
        got_ids = {i.id for i in items}
        if got_ids != expected_ids:
            missing = sorted(expected_ids - got_ids)
            extra = sorted(got_ids - expected_ids)
            problems.append(f"soundwave_30 ids: missing={missing} unexpected={extra}")

    return problems
