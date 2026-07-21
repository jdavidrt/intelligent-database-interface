"""Conformance report for all four benchmark corpora.

Usage:  python -m evaluation.validate

Checks everything EVALUATION_PROTOCOL.md fixes before a run: corpus sizes (§2),
manifest schema (§2.2), stratification and category counts (§2.1), executability
of every reference query against the frozen-clock database (§3.1), and the
amended §9 quirk 2 rule that EC-07 items may not carry accepted_alternatives.

Exit code is non-zero if any corpus is non-conformant, so this is usable as a
pre-run gate.
"""

from __future__ import annotations

import sys
from collections import Counter

from evaluation.corpus import CORPUS_SIZES, FREEZE_NOW, execute, load_corpus
from evaluation.hardness import (
    BIRD_FROM_SPIDER,
    EXEC_FROM_SPIDER,
    eval_hardness,
)


def main() -> int:
    print(f"IDI benchmark corpora — conformance report (frozen clock {FREEZE_NOW})\n")
    total_problems = 0
    total_items = 0
    total_executed = 0

    for name in CORPUS_SIZES:
        from evaluation.corpus import check_corpus

        items = load_corpus(name)
        problems = check_corpus(name)
        total_problems += len(problems)
        total_items += len(items)

        scorable = [i for i in items if i.expected_behaviour == "answer" and i.reference_sql]
        executed = sum(1 for i in scorable if execute(i.reference_sql)[1] is None)
        total_executed += executed

        status = "CONFORMANT" if not problems else f"{len(problems)} PROBLEM(S)"
        print(f"{name:14s} {len(items):3d} items   {executed}/{len(scorable)} execute   {status}")

        if name == "spider_style":
            print(
                f"  {'tiers (computed)':22s}",
                dict(Counter(eval_hardness(i.reference_sql) for i in scorable)),
            )
        elif name == "bird_style":
            print(
                f"  {'tiers (computed)':22s}",
                dict(Counter(BIRD_FROM_SPIDER[eval_hardness(i.reference_sql)] for i in scorable)),
            )
            print(f"  {'items with EC traps':22s}", sum(1 for i in items if i.ec_tags))
        elif name == "idi_exec_75":
            print(
                f"  {'levels (computed)':22s}",
                dict(Counter(EXEC_FROM_SPIDER[eval_hardness(i.reference_sql)] for i in scorable)),
            )
            print(
                f"  {'clarify items':22s}",
                sum(1 for i in items if i.expected_behaviour == "clarify"),
            )
        elif name == "soundwave_30":
            print(f"  {'tiers (as authored)':22s}", dict(Counter(i.difficulty for i in items)))

        # Items whose ground truth is empty are legitimate (§3.4, §9) but weak
        # discriminators, so they are surfaced rather than buried.
        empty = [i.id for i in scorable if not execute(i.reference_sql)[0]]
        if empty:
            print(f"  {'empty ground truth':22s} {len(empty)}  {', '.join(empty)}")

        for problem in problems:
            print(f"    ! {problem}")
        print()

    print(
        f"total: {total_items} items, {total_executed} reference queries execute, "
        f"{total_problems} problem(s)"
    )
    return 1 if total_problems else 0


if __name__ == "__main__":
    sys.exit(main())
