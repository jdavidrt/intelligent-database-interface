"""
A/B harness - EC suite with base instructions vs instruction profiles.

Run A: registry.json temporarily emptied  -> all agents on base instructions.
Run B: registry.json as authored          -> specialized profiles active.
Output: data/benchmarks/ab_report_<date>.json + console table.
Metrics per run: EC pass count (of 8), per-probe verification verdicts,
mean latency per query, generated-SQL exact-keyword hits (IS NULL, etc.).

Requires a live backend (+ llama.cpp) on http://localhost:5000, same
precondition as gate_d1.py. Run: python tests/ab_harness.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from gate_d1 import PROBES, run_query  # noqa: E402

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "adapters", "registry.json")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "benchmarks")


def _probe_passed(result: dict) -> bool:
    verify = result.get("verify") or {}
    return bool(verify.get("overall_passed")) and result.get("row_count", 0) > 0


def _keyword_hit(probe: dict, result: dict) -> bool | None:
    kw = probe.get("expected_keyword") or probe.get("expected_table")
    if not kw:
        return None
    sql = (result.get("sql") or {}).get("sql", "").upper()
    return kw.upper() in sql


def _run_all_probes(label: str) -> dict:
    print(f"\n--- Run {label} ---")
    verdicts = []
    latencies = []
    for probe in PROBES:
        t0 = time.time()
        try:
            result, events = run_query(probe["query"])
        except Exception as e:
            print(f"  [{probe['ec']}] ERROR: {e}")
            verdicts.append(
                {
                    "ec": probe["ec"],
                    "passed": False,
                    "row_count": 0,
                    "latency_ms": None,
                    "keyword_hit": None,
                    "adapters_seen": [],
                }
            )
            continue
        elapsed_ms = round((time.time() - t0) * 1000)
        latencies.append(elapsed_ms)
        passed = _probe_passed(result)
        adapters = sorted(
            {
                (e.get("payload") or {}).get("adapter")
                for e in events
                if (e.get("payload") or {}).get("adapter")
            }
        )
        verdict = {
            "ec": probe["ec"],
            "passed": passed,
            "row_count": result.get("row_count", 0),
            "latency_ms": elapsed_ms,
            "keyword_hit": _keyword_hit(probe, result),
            "adapters_seen": adapters,
        }
        verdicts.append(verdict)
        print(
            f"  [{probe['ec']}] {'PASS' if passed else 'FAIL'} "
            f"({elapsed_ms}ms, adapters={adapters})"
        )

    pass_count = sum(1 for v in verdicts if v["passed"])
    mean_latency = round(sum(latencies) / len(latencies)) if latencies else None
    return {
        "pass_count": pass_count,
        "of": len(PROBES),
        "mean_latency_ms": mean_latency,
        "probes": verdicts,
    }


def main() -> None:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        original_registry_bytes = f.read()

    run_a = None
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            f.write("{}")
        run_a = _run_all_probes("A (base — registry emptied)")
    finally:
        # Restore the real registry before Run B, and unconditionally — a
        # crash mid Run-A must never leave the repo in a broken state for
        # anyone testing the app afterward.
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            f.write(original_registry_bytes)

    run_b = _run_all_probes("B (specialized — registry as authored)")

    delta = {
        "pass_count": run_b["pass_count"] - run_a["pass_count"],
        "mean_latency_ms": (
            (run_b["mean_latency_ms"] or 0) - (run_a["mean_latency_ms"] or 0)
            if run_a["mean_latency_ms"] is not None and run_b["mean_latency_ms"] is not None
            else None
        ),
    }

    report = {
        "date": date.today().isoformat(),
        "base_url": "http://localhost:5000",
        "run_a_base": run_a,
        "run_b_specialized": run_b,
        "delta": delta,
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, f"ab_report_{report['date']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"{'EC':<8}{'Base':<8}{'Specialized':<14}")
    for a, b in zip(run_a["probes"], run_b["probes"]):
        print(
            f"{a['ec']:<8}{'PASS' if a['passed'] else 'FAIL':<8}"
            f"{'PASS' if b['passed'] else 'FAIL':<14}"
        )
    print(f"{'='*60}")
    print(
        f"Pass count — base: {run_a['pass_count']}/{run_a['of']}  "
        f"specialized: {run_b['pass_count']}/{run_b['of']}  delta: {delta['pass_count']:+d}"
    )
    print(
        f"Mean latency — base: {run_a['mean_latency_ms']}ms  "
        f"specialized: {run_b['mean_latency_ms']}ms"
    )
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
