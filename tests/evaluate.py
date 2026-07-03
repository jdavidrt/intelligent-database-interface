"""
Evaluation harness - the durable benchmark (distinct from the gate_d1.py
pass/fail gate). Reuses the EC-01..EC-08 probes and streaming client from
gate_d1.py. Requires a live backend (+ llama.cpp) on http://localhost:5000.

Three metrics:
  1. Execution accuracy - hand-derived expected values per probe, read
     directly from databases/soundwave/02_soundwave_data.sql (see CHECKERS
     below; each check function documents exactly which rows it was derived from).
  2. Latency per pipeline stage - computed from AgentEvent timestamps
     already present in the NDJSON stream, no backend change needed.
  3. Tokens/sec - read from the sql_generator "done" event payload, which
     llm_service.chat_with_meta() populates (see Day 3 Step 4 wiring in
     llm_service.py / sql_generator.py / orchestrator.py).

Known data quirk (documented, not a bug in this harness): EC-08 asks for
playlists containing tracks "by Adele", but no artist named Adele exists in
soundwave_db's 12-artist catalog. The correct answer is therefore 0 rows -
which means this probe can never satisfy gate_d1.py's/ab_harness.py's
row_count > 0 pass heuristic even with perfect SQL. EC-08's accuracy checker
here correctly expects 0 rows; its EC-08 gate/A-B "pass" will still read as
FAIL under the row-count heuristic used elsewhere. That's a probe-design
limitation inherited from gate_d1.py, not something this file works around.

Run: python tests/evaluate.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))
from gate_d1 import PROBES, run_query  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "benchmarks")


# -- Execution accuracy: hand-derived from databases/soundwave/02_soundwave_data.sql --


def _check_ec01(result: dict) -> str | None:
    """Only Karol G (artist_id=12) has country='CO' among the 12 artists."""
    rows = result.get("rows") or []
    if len(rows) != 1:
        return f"expected 1 row (Karol G), got {len(rows)}"
    values = [str(v).lower() for v in rows[0].values()]
    if not any("karol" in v for v in values):
        return f"expected a Karol G row, got {rows[0]}"
    return None


def _check_ec02(result: dict) -> str | None:
    """has_hifi=1 for plan_id 3 (Individual) and 4 (Family) only."""
    rows = result.get("rows") or []
    if len(rows) != 2:
        return f"expected 2 rows (Individual, Family), got {len(rows)}"
    names = {str(v).lower() for row in rows for v in row.values() if isinstance(v, str)}
    if not any("individual" in n for n in names):
        return "expected 'Individual' plan in results"
    if not any("family" in n for n in names):
        return "expected 'Family' plan in results"
    return None


def _check_ec03(result: dict) -> str | None:
    """Tracks 26-30 have album_id IS NULL -> 5 standalone singles."""
    rows = result.get("rows") or []
    if len(rows) != 1:
        return f"expected 1 row (a COUNT), got {len(rows)}"
    values = list(rows[0].values())
    if 5 not in values:
        return f"expected COUNT == 5, got {rows[0]}"
    return None


_EC04_GENRES = {"pop", "rock", "hip-hop", "latin", "r&b", "electronic"}


def _check_ec04(result: dict) -> str | None:
    """Genres referenced as some other genre's parent_genre_id: Pop, Rock,
    Hip-Hop, Latin, R&B, Electronic (Jazz and Classical have none)."""
    rows = result.get("rows") or []
    names = {str(v).lower() for row in rows for v in row.values() if isinstance(v, str)}
    missing = {g for g in _EC04_GENRES if not any(g in n for n in names)}
    if missing:
        return f"missing expected genres with subgenres: {sorted(missing)}"
    return None


def _check_ec05(result: dict) -> str | None:
    """sum(trk_dur_ms) across all 30 tracks = 6,567,447ms -> avg = 218,914.9ms
    = 3.648 minutes."""
    rows = result.get("rows") or []
    if len(rows) != 1:
        return f"expected 1 row (an AVG), got {len(rows)}"
    values = [v for v in rows[0].values() if isinstance(v, (int, float))]
    if not values:
        return f"expected a numeric average, got {rows[0]}"
    val = values[0]
    if not (3.4 <= val <= 3.9):
        return f"expected avg duration ~3.65 minutes, got {val}"
    return None


def _check_ec06(result: dict) -> str | None:
    """pricing_history row (plan_id=3, 9.99, '2024-01-01', NULL) is current."""
    rows = result.get("rows") or []
    if not rows:
        return "expected at least 1 row with the current price"
    values = [v for row in rows for v in row.values() if isinstance(v, (int, float))]
    if not any(abs(v - 9.99) < 0.001 for v in values):
        return f"expected price 9.99, got {values}"
    return None


def _check_ec08(result: dict) -> str | None:
    """No artist named 'Adele' exists in soundwave_db -> correct answer is 0 rows."""
    row_count = result.get("row_count", 0)
    if row_count != 0:
        return f"expected 0 rows (no artist named 'Adele' in soundwave_db), got {row_count}"
    return None


CHECKERS = {
    "EC-01": _check_ec01,
    "EC-02": _check_ec02,
    "EC-03": _check_ec03,
    "EC-04": _check_ec04,
    "EC-05": _check_ec05,
    "EC-06": _check_ec06,
    # EC-07 ("most plays last month") is date-relative against a dataset
    # frozen at 2025-01-20 - not fixed-derivable, intentionally not scored.
    "EC-08": _check_ec08,
}


def _score_accuracy(ec: str, result: dict) -> dict:
    checker = CHECKERS.get(ec)
    if checker is None:
        return {"accuracy": "not_scored"}
    failure = checker(result)
    return {"accuracy": "pass" if failure is None else "fail", "detail": failure}


# -- Latency per pipeline stage, from AgentEvent timestamps ---------------------


def _stage_latencies(events: list[dict]) -> dict[str, float]:
    starts: dict[str, datetime] = {}
    latencies: dict[str, float] = {}
    for e in events:
        agent = e.get("agent")
        status = e.get("status")
        ts = e.get("timestamp")
        if not agent or not ts:
            continue
        when = datetime.fromisoformat(ts)
        if status == "started" and agent not in starts:
            starts[agent] = when
        elif status in ("done", "error") and agent in starts:
            latencies[agent] = round((when - starts[agent]).total_seconds() * 1000)
    return latencies


# -- Tokens/sec, from the sql_generator "done" event payload --------------------


def _tokens_per_sec(events: list[dict]) -> float | None:
    for e in events:
        if e.get("agent") == "sql_generator" and e.get("status") == "done":
            return (e.get("payload") or {}).get("tokens_per_sec")
    return None


def main() -> None:
    print(f"\nEvaluation — running {len(PROBES)} EC probes\n{'='*60}")

    per_stage_latencies: dict[str, list[float]] = {}
    per_probe = []

    for probe in PROBES:
        ec = probe["ec"]
        try:
            result, events = run_query(probe["query"])
        except Exception as e:
            print(f"[{ec}] ERROR: {e}")
            per_probe.append({"ec": ec, "accuracy": "error", "detail": str(e)})
            continue

        accuracy = _score_accuracy(ec, result)
        stages = _stage_latencies(events)
        for agent, ms in stages.items():
            per_stage_latencies.setdefault(agent, []).append(ms)
        tps = _tokens_per_sec(events)

        entry = {"ec": ec, **accuracy, "stage_latencies_ms": stages, "tokens_per_sec": tps}
        per_probe.append(entry)
        print(f"[{ec}] accuracy={accuracy['accuracy']:<11} " f"tokens/sec={tps}  stages={stages}")

    mean_stage_latency = {
        agent: round(sum(vals) / len(vals)) for agent, vals in per_stage_latencies.items()
    }
    scored = [p for p in per_probe if p["accuracy"] in ("pass", "fail")]
    accuracy_summary = {
        "scored": len(scored),
        "passed": sum(1 for p in scored if p["accuracy"] == "pass"),
        "not_scored": sum(1 for p in per_probe if p["accuracy"] == "not_scored"),
    }

    report = {
        "date": date.today().isoformat(),
        "base_url": "http://localhost:5000",
        "accuracy_summary": accuracy_summary,
        "mean_stage_latency_ms": mean_stage_latency,
        "probes": per_probe,
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, f"eval_{report['date']}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_path = os.path.join(REPORT_DIR, f"eval_{report['date']}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Evaluation report — {report['date']}\n\n")
        f.write(
            f"Accuracy: {accuracy_summary['passed']}/{accuracy_summary['scored']} "
            f"scored probes passed ({accuracy_summary['not_scored']} not scored)\n\n"
        )
        f.write("| EC | Accuracy | Detail | Tokens/sec |\n|---|---|---|---|\n")
        for p in per_probe:
            f.write(
                f"| {p['ec']} | {p['accuracy']} | {p.get('detail') or ''} | "
                f"{p.get('tokens_per_sec')} |\n"
            )
        f.write("\n## Mean latency per stage (ms)\n\n")
        for agent, ms in mean_stage_latency.items():
            f.write(f"- {agent}: {ms}ms\n")

    print(f"\n{'='*60}")
    print(
        f"Accuracy: {accuracy_summary['passed']}/{accuracy_summary['scored']} scored "
        f"({accuracy_summary['not_scored']} not scored)"
    )
    print(f"Mean stage latency: {mean_stage_latency}")
    print(f"Reports written to {json_path} and {md_path}")


if __name__ == "__main__":
    main()
