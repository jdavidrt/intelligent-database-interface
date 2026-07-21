"""IDI — interactive benchmark runner.

Runs the four frozen corpora of `docs/EVALUATION_PROTOCOL.md` §2 — Spider-style,
BIRD-style, IDI-EXEC-75 and SoundWave-30, 225 items in all — against the live
pipeline, and offers four presets so the operator can pick a sweep that fits the
time available:

    30 minutes   20 items, easy-weighted   smoke test
    1 hour       41 items                  pilot
    3 hours     123 items                  pilot
    full        225 items                  the only reportable option (~5h 30m)

Counts are sized against the measured 87.6s/item of the 2026-07-21 pilot and are
fixed constants; the menu shows a live estimate from the newest report on disk.

Usage — this is the whole command. No other server or terminal is needed:

    python run_benchmarks.py                  # menu
    python run_benchmarks.py --profile 30m    # unattended
    python run_benchmarks.py --profile full --tag "run B, specialized profiles"

llama.cpp and the FastAPI backend are started automatically if they are not
already up, with `IDI_FREEZE_NOW` and `IDI_GREEDY` set — the two settings whose
absence silently voids a run (§1.1, §1.3). Anything this process started is
stopped when the run ends; anything already running is adopted and left alone,
including on Ctrl-C. Pass `--no-autostart` to require a backend you manage
yourself.

Everything of substance lives in `evaluation/`: this file is a menu, a preflight
banner and a progress display. Selection (`evaluation/plan.py`), scoring
(`evaluation/scoring.py`), reporting (`evaluation/run.py`) and process
management (`evaluation/servers.py`) are shared with `python -m evaluation.run`,
so the two entry points cannot disagree about what a run means.

The §1.1 frozen clock is set before any import that touches services.clock.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# Must precede the evaluation imports: evaluation.corpus pins IDI_FREEZE_NOW at
# import time and the clock service reads it once, at its own import.
os.environ.setdefault("IDI_FREEZE_NOW", "2026-07-17T12:00:00")

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from evaluation import run as runner  # noqa: E402
from evaluation.plan import (  # noqa: E402
    PROFILES,
    TOTAL_ITEMS,
    estimate_seconds,
    format_duration,
    plan_run,
)
from evaluation.progress import ProgressReporter  # noqa: E402
from evaluation.servers import ManagedServers  # noqa: E402

REPORT_GLOB = os.path.join(ROOT, "data", "benchmarks", "eval_*.json")


# -- duration estimates --------------------------------------------------------


def measured_seconds_per_item() -> tuple[float | None, str]:
    """Per-item cost from the newest scored report, if one is in the new format.

    Display only — the presets are fixed item counts (a preset that resized
    itself between runs would make two "1 hour runs" incomparable), so this
    changes the *label*, never the selection.
    """
    for path in sorted(glob.glob(REPORT_GLOB), reverse=True):
        try:
            with open(path, encoding="utf-8") as handle:
                report = json.load(handle)
            p50 = report["summary"]["latency_ms"]["end_to_end"]["p50"]
        except Exception:
            continue
        if p50:
            return p50 / 1000, os.path.basename(path)
    return None, "no prior run in this format — 2026-07-14 measurement"


# -- menu ----------------------------------------------------------------------


def print_menu(seconds_per_item: float | None, source: str) -> list[str]:
    keys = list(PROFILES)
    print("\n  IDI benchmark runner — 4 corpora, 225 items (EVALUATION_PROTOCOL.md §2)")
    print(f"  timing estimated at {estimate_seconds(1, seconds_per_item):.0f}s/item ({source})\n")
    for number, key in enumerate(keys, start=1):
        profile = PROFILES[key]
        estimate = format_duration(estimate_seconds(profile.size, seconds_per_item))
        head = f"   [{number}] {profile.label:<12} {profile.size:>3} items  {estimate:>8}"
        print(f"{head}   {profile.note}")
    print("   [q] quit\n")

    gap = estimate_seconds(TOTAL_ITEMS - PROFILES["3h"].size, seconds_per_item)
    print(
        f"  Only the full run is reportable as a §3 corpus EX; it is "
        f"{format_duration(gap).lstrip('~')} longer than [3]. Everything shorter is a\n"
        f"  pilot figure, and [1] is easy-weighted on top of that.\n"
    )
    return keys


def ask(prompt: str, options: list[str], default: str) -> str:
    while True:
        answer = input(f"  {prompt} [{'/'.join(options)}] ({default}): ").strip().lower()
        if not answer:
            return default
        if answer in options:
            return answer
        print(f"  not one of {options}")


def choose_profile(seconds_per_item: float | None, source: str) -> str:
    keys = print_menu(seconds_per_item, source)
    while True:
        answer = input("  select > ").strip().lower()
        if answer in ("q", "quit", "exit"):
            raise SystemExit("  nothing run.")
        if answer in keys:
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(keys):
            return keys[int(answer) - 1]
        print(f"  pick 1-{len(keys)} or q")


# -- run banner ----------------------------------------------------------------


def print_plan(header: dict, items_count: int, seconds_per_item: float | None) -> None:
    selection = header["selection"]
    print("\n" + "=" * 78)
    print(f"  {selection['profile_label']} — {items_count} items")
    print(f"  engine    : {header['engine']['description']}")
    print(f"  database  : {header['engine']['database']}")
    print(f"  decoding  : greedy={header['decoding']['greedy']} seed={header['decoding']['seed']}")
    print(f"  clock     : {header['freeze_now']}")
    print(f"  hardware  : {header['hardware']['profile']} — {header['hardware']['gpu']}")
    print(f"  adapters  : Run {header['adapters'].get('run')}")
    print(f"  rule      : {selection['rule']}")
    print(
        "  mix       : "
        + ", ".join(f"{tier} {count}" for tier, count in selection["tier_totals"].items())
        + "  (normalized axis; reports use native tier labels)"
    )
    for name, counts in selection["per_corpus_tier"].items():
        total = sum(counts.values())
        detail = ", ".join(f"{tier} {count}" for tier, count in counts.items())
        print(f"    {name:<14} {total:>3}   ({detail})")
    print(f"  estimate  : {format_duration(estimate_seconds(items_count, seconds_per_item))}")
    if not header["reportable"]:
        print("\n  NOT REPORTABLE as a §3 corpus EX:")
    for caveat in header["caveats"]:
        print(f"    ! {caveat}")
    print("=" * 78 + "\n")


# -- main ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the IDI benchmark corpora (§3).")
    parser.add_argument(
        "--profile",
        choices=list(PROFILES),
        help="skip the menu and run this preset unattended",
    )
    parser.add_argument("--corpus", action="append", default=None, help="restrict to one corpus")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="do not start llama.cpp or the backend; require them to be running already",
    )
    runner.add_common_arguments(parser)
    args = parser.parse_args()

    seconds_per_item, source = measured_seconds_per_item()

    # Everything this block starts is owned by the `with`, so a crash, a
    # SystemExit from preflight or a Ctrl-C all take the same teardown path.
    # Servers that were already running are never in `started` and survive.
    with ManagedServers() as servers:
        if args.no_autostart:
            print(f"\n  --no-autostart: expecting a backend at {args.base_url}")
        else:
            print("\n  bringing up the servers this run needs …")
            servers.ensure_all(args.base_url)

        # preflight owns the §1.1/§1.3 verdict, whether we started the backend
        # or adopted one that was already up.
        health = runner.preflight(args.base_url, args.allow_unfrozen)
        print(
            f"  ready — clock {health.get('freeze_now')}, greedy={health.get('greedy')}, "
            f"db '{runner.DB_NAME}' selected"
        )

        profile = args.profile or choose_profile(seconds_per_item, source)
        corpora = args.corpus or list(runner.CORPUS_SIZES)
        items, selection = plan_run(profile, corpora)

        header = runner.build_header(args.base_url, health, args.hardware_profile, selection, args)
        if args.allow_unfrozen and health.get("freeze_now") != runner.FREEZE_NOW:
            header["reportable"] = False
            header["caveats"].append("§1.1 VOID: executed without the frozen clock")

        print_plan(header, len(items), seconds_per_item)
        if not args.yes and not args.profile and ask("start?", ["y", "n"], "y") != "y":
            raise SystemExit("  nothing run.")

        reporter = ProgressReporter(total=len(items))
        summary, _records, json_path, md_path = runner.run_sweep(items, header, args, reporter)
        runner.print_summary(header, summary, json_path, md_path)


if __name__ == "__main__":
    main()
