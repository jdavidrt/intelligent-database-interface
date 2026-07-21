"""Scored-run harness — EVALUATION_PROTOCOL.md §3, executed against a live pipeline.

Feeds each corpus item's `nl` through POST /query exactly as the frontend does,
captures the generated SQL, the returned rows, the verification report and the
AgentEvent timings, and scores the result per §3.2–§3.6. Writes
`data/benchmarks/eval_<date>.{json,md}`.

What this harness refuses to do is as important as what it does:

- **It will not write a report from an unfrozen server.** §1.1 voids any run
  executed without `IDI_FREEZE_NOW`. The clock lives in the *backend* process,
  so the check reads `GET /health` — verifying the harness's own environment
  would prove nothing about the process that generated the SQL.
- **It never stores ground truth.** §3.1 defines ground truth as the result of
  executing `reference_sql` at run time, so `evaluation.corpus.execute` is
  called for every item on every run. A stale expected value cannot creep in.
- **It selects its subset before seeing any result.** A run that cannot afford
  all 225 items takes a deterministic manifest-order prefix, allocated
  proportionally across the four corpora, fixed before the first query is sent
  and recorded in the header. Choosing which items to report after seeing the
  scores is the post-hoc tuning §0 exists to prevent.
- **A blocked query is a failure, not an empty answer.** §3.4 — verification
  blocking the SQL also yields zero rows, and scoring that as a pass whenever
  ground truth is empty would be a false positive (the Adele case, §9 quirk 1).

Usage (backend, llama.cpp and the frozen clock must already be running):

    python -m evaluation.run --profile 30m                    # a preset (see plan.py)
    python -m evaluation.run --total 30 --hardware-profile gpu
    python -m evaluation.run --corpus soundwave_30            # one full corpus
    python -m evaluation.run                                  # all 225 items

`run_benchmarks.py` at the repo root wraps this with a menu and a live progress
display; everything below is shared with it rather than duplicated.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import requests

from evaluation.corpus import CORPUS_SIZES, FREEZE_NOW, CorpusItem, execute
from evaluation.plan import PROFILES, plan_run, select_items, selection_caveats
from evaluation.progress import ProgressReporter
from evaluation.scoring import Comparison, compare_against_any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(REPO_ROOT, "data", "benchmarks")
DEFAULT_BASE_URL = "http://localhost:5000"
DB_NAME = "soundwave"

# The connector force-appends LIMIT 200 to any query without one
# (file_connector.execute_read). No corpus item's ground truth reaches that, but
# a future one could, and it would look like a model error rather than an
# instrument artefact — so it is checked per item and reported.
CONNECTOR_ROW_CAP = 200


# -- the pipeline client -------------------------------------------------------


def _post_stream(
    base_url: str,
    nl: str,
    timeout: int,
    on_event: Callable[[dict], None] | None = None,
) -> tuple[dict, list[dict], int]:
    """Send one question to /query. Returns (result, events, wall_ms).

    No `session_id` is sent, so every item runs in a fresh session: the
    orchestrator injects the last four turns into intent parsing, which would
    otherwise let item N contaminate item N+1.

    `on_event` is called for each AgentEvent as it arrives, which is what makes
    a live "current step" display possible; it is purely observational.
    """
    started = time.time()
    response = requests.post(
        f"{base_url}/query", json={"message": nl}, stream=True, timeout=timeout
    )
    response.raise_for_status()
    result: dict = {}
    events: list[dict] = []
    for line in response.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        if data.get("type") == "result":
            result = data
        else:
            events.append(data)
            if on_event is not None:
                on_event(data)
    return result, events, round((time.time() - started) * 1000)


def _stage_latencies(events: list[dict]) -> dict[str, int]:
    """Per-agent elapsed ms, from AgentEvent timestamps (§5's measured span)."""
    starts: dict[str, datetime] = {}
    latencies: dict[str, int] = {}
    for event in events:
        agent, status, stamp = event.get("agent"), event.get("status"), event.get("timestamp")
        if not agent or not stamp:
            continue
        when = datetime.fromisoformat(stamp)
        if status == "started" and agent not in starts:
            starts[agent] = when
        elif status in ("done", "error") and agent in starts:
            latencies[agent] = round((when - starts[agent]).total_seconds() * 1000)
    return latencies


def _tokens_per_sec(events: list[dict]) -> float | None:
    for event in events:
        if event.get("agent") == "sql_generator" and event.get("status") == "done":
            return (event.get("payload") or {}).get("tokens_per_sec")
    return None


def _clarification_question(events: list[dict]) -> str | None:
    for event in events:
        payload = event.get("payload") or {}
        if payload.get("clarification_question"):
            return payload["clarification_question"]
    return None


def _is_meta_answer(events: list[dict]) -> bool:
    return any((event.get("payload") or {}).get("meta_answer") for event in events)


def _verify_caveats(verify: dict) -> list[str]:
    """The three layers' caveats, flattened (VerifyReport.caveats over the wire)."""
    return [
        caveat
        for layer_name in ("syntax", "semantic", "sanity")
        for caveat in (verify.get(layer_name) or {}).get("caveats", [])
    ]


def _verdict(verify: dict) -> str | None:
    """VerifyReport.verdict, recomputed client-side (§4.4's pass/caution/fail).

    A `caution` never blocks: the query executed and the caveat rode into the
    answer, so it is a usability signal here, not a failure.
    """
    if not verify:
        return None
    if not verify.get("overall_passed"):
        return "fail"
    return "caution" if _verify_caveats(verify) else "pass"


# -- §3.4 / §3.6 scoring -------------------------------------------------------


def _classify(result: dict, events: list[dict]) -> str:
    """What the pipeline actually did, independent of whether it was right.

    The distinction between `blocked` and `answered` is what makes §3.4
    enforceable: both can report zero rows.
    """
    verify = result.get("verify") or {}
    if _clarification_question(events):
        return "clarified"
    if _is_meta_answer(events):
        return "meta_answer"
    if not (result.get("sql") or {}).get("sql"):
        return "no_sql"
    if verify and not verify.get("overall_passed"):
        return "blocked"
    if result.get("error"):
        return "pipeline_error"
    return "answered"


def score_item(
    item: CorpusItem,
    result: dict,
    events: list[dict],
    truths: list[list[tuple]] | None,
) -> dict[str, Any]:
    """Score one item per §3.4 (non-answers) and §3.6 (expected_behaviour)."""
    outcome = _classify(result, events)
    rows = result.get("rows") or []

    if item.expected_behaviour == "clarify":
        # §3.6: pass iff the pipeline requests clarification instead of
        # guessing. Producing SQL is a fail even if that SQL is reasonable.
        passed = outcome == "clarified"
        reason = (
            f"asked: {_clarification_question(events)}"
            if passed
            else f"did not clarify (pipeline {outcome})"
        )
        return {"score": "pass" if passed else "fail", "outcome": outcome, "reason": reason}

    if item.expected_behaviour == "block":
        passed = outcome == "blocked"
        return {
            "score": "pass" if passed else "fail",
            "outcome": outcome,
            "reason": "verification blocked it" if passed else f"not blocked (pipeline {outcome})",
        }

    # expected_behaviour == "answer"
    if truths is None:
        # The reference SQL itself failed to execute: a corpus defect, not a
        # model failure. Excluded from the EX denominator and reported loudly
        # rather than silently scored as a fail.
        return {"score": "void", "outcome": outcome, "reason": "reference_sql did not execute"}

    if outcome == "blocked":
        # §3.4: nothing executed. Also an EDR event (§4).
        verify = result.get("verify") or {}
        failing = "; ".join(
            layer.get("message", "")
            for name in ("syntax", "semantic", "sanity")
            for layer in [verify.get(name) or {}]
            if not layer.get("passed", True)
        )
        return {
            "score": "fail",
            "outcome": outcome,
            "reason": f"verification blocked the SQL — {failing}",
            "edr_event": True,
        }
    if outcome == "clarified":
        return {"score": "fail", "outcome": outcome, "reason": "ended in clarification (§3.4)"}
    if outcome == "meta_answer":
        return {"score": "fail", "outcome": outcome, "reason": "answered as a meta question"}
    if outcome == "no_sql":
        return {"score": "fail", "outcome": outcome, "reason": "no SQL generated"}
    if outcome == "pipeline_error":
        return {
            "score": "fail",
            "outcome": outcome,
            "reason": f"pipeline error: {result.get('error')}",
        }

    comparison: Comparison = compare_against_any(truths, rows, order_matters=item.order_matters)
    return {
        "score": "pass" if comparison.matched else "fail",
        "outcome": outcome,
        "reason": comparison.reason,
    }


# -- ground truth (§3.1) -------------------------------------------------------


def ground_truth(item: CorpusItem) -> tuple[list[list[tuple]] | None, dict[str, Any]]:
    """Execute the reference SQL (and any accepted alternatives) right now."""
    if item.expected_behaviour != "answer" or not item.reference_sql:
        return None, {}
    rows, error = execute(item.reference_sql)
    if error:
        return None, {"ground_truth_error": error}
    truths = [rows]
    for alternative in item.accepted_alternatives:
        alt_rows, alt_error = execute(alternative)
        if not alt_error:
            truths.append(alt_rows)
    meta: dict[str, Any] = {"ground_truth_rows": len(rows)}
    if len(rows) >= CONNECTOR_ROW_CAP:
        meta["truncation_risk"] = (
            f"ground truth has {len(rows)} rows and the connector caps results at "
            f"{CONNECTOR_ROW_CAP} — a correct candidate would be scored fail"
        )
    return truths, meta


# -- run header (§1.1–§1.4) ----------------------------------------------------


def _git_sha() -> dict[str, Any]:
    def _run(*args: str) -> str:
        try:
            return subprocess.run(
                args, cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception:
            return ""

    return {
        "sha": _run("git", "rev-parse", "HEAD"),
        "dirty": bool(_run("git", "status", "--porcelain")),
    }


def _llama_props(base_url: str) -> dict[str, Any]:
    """Model and GPU-offload facts, read off llama.cpp rather than assumed."""
    url = base_url.replace(":5000", ":7860")
    try:
        response = requests.get(f"{url}/props", timeout=5)
        response.raise_for_status()
        props = response.json()
        settings = props.get("default_generation_settings", {})
        return {
            "model_path": props.get("model_path") or settings.get("model"),
            "n_ctx": settings.get("n_ctx"),
        }
    except Exception:
        return {}


def _gpu_name() -> str | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        return out.splitlines()[0] if out else None
    except Exception:
        return None


def _adapter_registry() -> dict[str, Any]:
    """§6: Run A (empty registry) vs Run B (as authored) must be distinguishable."""
    path = os.path.join(REPO_ROOT, "adapters", "registry.json")
    try:
        with open(path, encoding="utf-8") as handle:
            mapping = json.load(handle)
        return {"registry": mapping, "run": "A (baseline, empty registry)" if not mapping else "B"}
    except Exception as exc:
        return {"registry": None, "error": str(exc)}


def build_header(
    base_url: str, health: dict, hardware_profile: str, selection: dict, args: argparse.Namespace
) -> dict[str, Any]:
    greedy = bool(health.get("greedy"))
    caveats: list[str] = []
    if not greedy:
        caveats.append(
            "§1.3: decoding is NOT greedy — this run is reportable only alongside "
            "n>=3 repetitions with mean and spread. Set IDI_GREEDY=1 on the backend."
        )
    if selection["subset"]:
        caveats.append(
            f"partial run: {selection['selected']} of {sum(CORPUS_SIZES.values())} items. "
            "EX below is a pilot figure, not the corpus EX of §3."
        )
    # Whatever else the selection rule skewed — an easy-weighted preset, or a
    # subset that never exercises §3.6's clarify/block behaviour.
    caveats.extend(selection_caveats(selection))
    if health.get("connector") != "file":
        caveats.append(
            f"engine is {health.get('connector')!r}; EX is not comparable across engines (§1.2)"
        )

    return {
        "protocol_version": "1.2",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        # §1.2 — engine. EX is not comparable across engines without it.
        "engine": {
            "connector": health.get("connector"),
            "description": (
                "in-memory SQLite built from databases/soundwave/*.sql via FileConnector"
                if health.get("connector") == "file"
                else str(health.get("connector"))
            ),
            "database": health.get("active_db") or DB_NAME,
            "reset_to_seed": "per backend start; the connector is read-only and never mutated",
            "row_cap": CONNECTOR_ROW_CAP,
        },
        # §1.3 — decoding.
        "decoding": {
            "greedy": greedy,
            "temperature": 0.0 if greedy else "per-agent (0.0–0.4)",
            "top_p": 1.0 if greedy else None,
            "seed": health.get("greedy_seed"),
            "repetitions": 1,
            "constrained_planning": health.get("constrained_planning"),
            **_llama_props(base_url),
        },
        # §1.1 — frozen clock, read off the server, not off this process.
        "freeze_now": health.get("freeze_now"),
        # §1.4 — hardware profile.
        "hardware": {"profile": hardware_profile, "gpu": _gpu_name()},
        "git": _git_sha(),
        "adapters": _adapter_registry(),
        "selection": selection,
        "reportable": greedy and not selection["subset"],
        "caveats": caveats,
        "command": " ".join(sys.argv),
        "tag": args.tag,
    }


# -- subset selection ----------------------------------------------------------
#
# `select_items` (legacy --total/--per-corpus) and `plan_run` (the --profile
# presets) both live in evaluation/plan.py, so every selection rule sits in one
# offline-testable module. They are imported above and re-exported here for
# callers that already reach for `evaluation.run.select_items`.


# -- aggregation ---------------------------------------------------------------


def _breakdown(
    records: list[dict], key: str, *, qualify_by_corpus: bool = False
) -> dict[str, dict[str, int]]:
    """Pass rate per bucket, dropping void items from both numerator and denominator.

    `qualify_by_corpus` prefixes the bucket with its corpus, and §2.1 forces it
    on for `category` and `difficulty`: the four corpora speak four tier
    vocabularies (spider easy/medium/hard/extra, bird simple/moderate/
    challenging, soundwave Easy/Medium/Hard/Extra Hard, exec low/medium/high)
    and two of them use the token `medium` for different things. Pooling those
    into one table silently averages incomparable scales — and pools
    `Easy` with `easy` as two rows purely by capitalisation.

    EC tags are the exception and stay pooled: EC-01…EC-08 name the same
    stress pattern whichever corpus raises it, which is what §4.2 wants counted.
    """
    out: dict[str, dict[str, int]] = {}
    for record in records:
        values = record[key] if isinstance(record[key], list) else [record[key]]
        for value in values or ["(none)"]:
            label = f"{record['corpus']} / {value}" if qualify_by_corpus else str(value)
            bucket = out.setdefault(label, {"scored": 0, "passed": 0})
            if record["score"] == "void":
                continue
            bucket["scored"] += 1
            bucket["passed"] += record["score"] == "pass"
    return {k: v for k, v in sorted(out.items()) if v["scored"]}


def aggregate(records: list[dict]) -> dict[str, Any]:
    def ex(subset: list[dict]) -> dict[str, Any]:
        scored = [r for r in subset if r["score"] in ("pass", "fail")]
        passed = sum(1 for r in scored if r["score"] == "pass")
        return {
            "scored": len(scored),
            "passed": passed,
            "ex": round(passed / len(scored), 4) if scored else None,
            "void": sum(1 for r in subset if r["score"] == "void"),
        }

    corpora = sorted({r["corpus"] for r in records})
    return {
        "overall": ex(records),
        "per_corpus": {name: ex([r for r in records if r["corpus"] == name]) for name in corpora},
        "by_category": _breakdown(records, "category", qualify_by_corpus=True),
        "by_difficulty": _breakdown(records, "difficulty", qualify_by_corpus=True),
        "by_ec_tag": _breakdown(records, "ec_tags"),
        "outcomes": {
            outcome: sum(1 for r in records if r["outcome"] == outcome)
            for outcome in sorted({r["outcome"] for r in records})
        },
        "verdicts": {
            verdict: sum(1 for r in records if r["verdict"] == verdict)
            for verdict in sorted({r["verdict"] for r in records if r["verdict"]})
        },
        "edr_events": sum(1 for r in records if r.get("edr_event")),
        "latency_ms": _latency_summary(records),
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return round(ordered[index], 1)


def _latency_summary(records: list[dict]) -> dict[str, Any]:
    """Descriptive only. §5's contract metric has its own measurement protocol
    (SPIDER-001..010, 5 repetitions, warm-up discarded) which this harness does
    not implement — these figures must not be quoted as the §5 P50."""
    wall = [r["wall_ms"] for r in records if r.get("wall_ms")]
    verification = [
        r["stage_latencies_ms"]["verification"]
        for r in records
        if r.get("stage_latencies_ms", {}).get("verification")
    ]
    tokens = [r["tokens_per_sec"] for r in records if r.get("tokens_per_sec")]
    return {
        "note": "descriptive; not the §5 measurement protocol",
        "end_to_end": {
            "p50": _percentile(wall, 0.5),
            "p90": _percentile(wall, 0.9),
            "max": max(wall, default=None),
        },
        "verification_chain": {"p50": _percentile(verification, 0.5)},
        "tokens_per_sec": {
            "p50": _percentile(tokens, 0.5),
            "mean": round(sum(tokens) / len(tokens), 2) if tokens else None,
        },
    }


# -- reporting -----------------------------------------------------------------


def _report_paths(overwrite: str | None = None) -> tuple[str, str]:
    """`eval_<date>.{json,md}`, never overwriting an existing scored run.

    A run costs ~40 minutes of inference and its per-item records are the
    evidence behind a published figure, so a second run on the same day gets a
    time suffix rather than silently replacing the first. `overwrite` is used
    only by `--rerender`, which recomputes a report's tables from records that
    are already on disk.
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    if overwrite:
        stem = os.path.splitext(overwrite)[0]
        return stem + ".json", stem + ".md"
    stem = f"eval_{datetime.now().date().isoformat()}"
    candidate = os.path.join(REPORT_DIR, stem)
    if os.path.exists(candidate + ".json"):
        candidate = os.path.join(REPORT_DIR, f"{stem}_{datetime.now().strftime('%H%M')}")
    return candidate + ".json", candidate + ".md"


def rerender(path: str) -> tuple[str, str]:
    """Recompute a saved run's summary and rewrite both files, in place.

    Fixing a bug in how results are *summarised* must not require re-running
    the pipeline: the per-item records are the measurement, and the tables are
    a view over them. Nothing here re-scores an item — `score`, `outcome` and
    `reason` are read back exactly as the run wrote them.
    """
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    header = report["header"]
    header.setdefault("rerendered_at", [])
    header["rerendered_at"].append(datetime.now(timezone.utc).isoformat())
    return write_reports(header, aggregate(report["items"]), report["items"], overwrite=path)


def _md_table(title: str, rows: dict[str, dict[str, int]]) -> str:
    if not rows:
        return ""
    out = [f"\n### {title}\n", "| Bucket | EX | Passed | Scored |", "|---|---|---|---|"]
    for name, bucket in rows.items():
        share = bucket["passed"] / bucket["scored"] if bucket["scored"] else 0
        out.append(f"| {name} | {share:.1%} | {bucket['passed']} | {bucket['scored']} |")
    return "\n".join(out) + "\n"


def write_reports(
    header: dict, summary: dict, records: list[dict], overwrite: str | None = None
) -> tuple[str, str]:
    json_path, md_path = _report_paths(overwrite)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(
            {"header": header, "summary": summary, "items": records}, handle, indent=2, default=str
        )

    lines: list[str] = []
    add = lines.append
    add(f"# IDI scored run — {header['started_at'][:10]}\n")
    if not header["reportable"]:
        add("> **Not reportable as a §3 corpus EX.**\n")
    for caveat in header["caveats"]:
        add(f"> - {caveat}")
    add("")
    add("## Run header\n")
    add("| Field | Value |")
    add("|---|---|")
    add(f"| Protocol | v{header['protocol_version']} |")
    add(f"| Engine (§1.2) | {header['engine']['description']} |")
    add(f"| Database | {header['engine']['database']} |")
    decoding = header["decoding"]
    add(
        f"| Decoding (§1.3) | greedy={decoding['greedy']}, "
        f"temperature={decoding['temperature']}, top_p={decoding['top_p']}, "
        f"seed={decoding['seed']}, repetitions={decoding['repetitions']} |"
    )
    add(f"| Constrained planning | {decoding.get('constrained_planning')} |")
    add(f"| Model | {decoding.get('model_path')} |")
    add(f"| IDI_FREEZE_NOW (§1.1) | {header['freeze_now']} |")
    add(f"| Hardware (§1.4) | {header['hardware']['profile']} — {header['hardware']['gpu']} |")
    add(f"| Git SHA | {header['git']['sha']}{' (dirty)' if header['git']['dirty'] else ''} |")
    add(f"| Adapters (§6) | Run {header['adapters'].get('run')} |")
    add(f"| Selection | {header['selection']['rule']} — {header['selection']['selected']} items |")
    tier_totals = header["selection"].get("tier_totals")
    if tier_totals:
        # The achieved difficulty mix, on the planner's normalized axis. Stated
        # because an easy-weighted subset flatters EX and the reader must see
        # by how much; the per-tier EX tables below use native corpus labels.
        add(
            "| Difficulty mix (normalized) | "
            + ", ".join(f"{tier} {count}" for tier, count in tier_totals.items())
            + " |"
        )

    add("\n## Execution Accuracy (§3)\n")
    overall = summary["overall"]
    overall_ex = f"{overall['ex']:.1%}" if overall["ex"] is not None else "n/a"
    void_note = f", {overall['void']} void" if overall["void"] else ""
    add(
        f"**Overall EX: {overall_ex}** "
        f"({overall['passed']}/{overall['scored']} scored{void_note})\n"
    )
    add("| Corpus | EX | Passed | Scored |")
    add("|---|---|---|---|")
    for name, bucket in summary["per_corpus"].items():
        share = f"{bucket['ex']:.1%}" if bucket["ex"] is not None else "—"
        add(f"| {name} | {share} | {bucket['passed']} | {bucket['scored']} |")

    add(_md_table("By category", summary["by_category"]))
    add(_md_table("By difficulty tier", summary["by_difficulty"]))
    add(_md_table("By EC stress pattern", summary["by_ec_tag"]))

    add("\n## Pipeline outcomes\n")
    for outcome, count in summary["outcomes"].items():
        add(f"- {outcome}: {count}")
    add(f"- verification-blocked (EDR events, §4): {summary['edr_events']}")
    add(
        "\nVerifier verdicts (§4.4): "
        + ", ".join(f"{k}={v}" for k, v in summary["verdicts"].items())
    )

    latency = summary["latency_ms"]
    add(f"\n## Latency — {latency['note']}\n")
    add(
        f"- end-to-end P50 {latency['end_to_end']['p50']}ms / P90 {latency['end_to_end']['p90']}ms "
        f"/ max {latency['end_to_end']['max']}ms"
    )
    add(f"- verification chain P50 {latency['verification_chain']['p50']}ms")
    tokens = latency["tokens_per_sec"]
    add(f"- tokens/sec P50 {tokens['p50']}, mean {tokens['mean']}")

    add("\n## Per-item results\n")
    add("| Item | Corpus | Tier | Score | Outcome | Verdict | Reason | SQL |")
    add("|---|---|---|---|---|---|---|---|")
    for record in records:
        sql = (record.get("sql") or "").replace("\n", " ").replace("|", "\\|")[:160]
        reason = (record.get("reason") or "").replace("|", "\\|")[:160]
        add(
            f"| {record['id']} | {record['corpus']} | {record['difficulty']} | {record['score']} | "
            f"{record['outcome']} | {record.get('verdict') or ''} | {reason} | `{sql}` |"
        )

    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return json_path, md_path


# -- preflight -----------------------------------------------------------------


def preflight(base_url: str, allow_unfrozen: bool) -> dict:
    try:
        health = requests.get(f"{base_url}/health", timeout=10).json()
    except Exception as exc:
        raise SystemExit(f"Backend unreachable at {base_url}: {exc}\nStart it with start.py.")

    if "freeze_now" not in health:
        raise SystemExit(
            "This backend's /health does not report freeze_now, so the §1.1 frozen-clock "
            "condition cannot be verified. Restart the backend on current code."
        )
    if health.get("freeze_now") != FREEZE_NOW and not allow_unfrozen:
        raise SystemExit(
            f"Refusing to run: the backend reports IDI_FREEZE_NOW={health.get('freeze_now')!r}, "
            f"expected {FREEZE_NOW!r}. §1.1 — a run without the frozen clock is void.\n"
            f"Restart the backend with IDI_FREEZE_NOW={FREEZE_NOW}."
        )
    if not health.get("llm_healthy"):
        raise SystemExit(
            "Refusing to run: llama.cpp is not healthy (GET /health -> llm_healthy=false)."
        )

    requests.post(
        f"{base_url}/db/select", json={"db_name": DB_NAME}, timeout=180
    ).raise_for_status()
    return requests.get(f"{base_url}/health", timeout=10).json()


# -- the sweep -----------------------------------------------------------------


def run_sweep(
    items: list[CorpusItem],
    header: dict,
    args: argparse.Namespace,
    reporter: ProgressReporter | None = None,
) -> tuple[dict, list[dict], str, str]:
    """Execute the selected items, score each, and write the reports.

    Shared by `python -m evaluation.run` and by `run_benchmarks.py`; the only
    difference between them is whether a `reporter` is supplied for the live
    display. Returns (summary, records, json_path, md_path).
    """
    records: list[dict] = []
    deadline = time.time() + args.minutes * 60 if getattr(args, "minutes", None) else None

    def emit(line: str) -> None:
        reporter.note(line) if reporter else print(line)

    try:
        for index, item in enumerate(items, start=1):
            if deadline and time.time() > deadline:
                header["caveats"].append(
                    f"wall-clock budget of {args.minutes} min reached after {index - 1} items; "
                    f"{len(items) - index + 1} selected items were not attempted"
                )
                header["reportable"] = False
                emit(f"[budget] stopping after {index - 1} items")
                break

            if reporter:
                reporter.start_item(index, item.id)
            truths, truth_meta = ground_truth(item)
            try:
                result, events, wall_ms = _post_stream(
                    args.base_url, item.nl, args.timeout, reporter.on_event if reporter else None
                )
            except Exception as exc:
                result, events, wall_ms = {"error": f"{type(exc).__name__}: {exc}"}, [], 0

            scored = score_item(item, result, events, truths)
            verify = result.get("verify") or {}

            record = {
                "id": item.id,
                "corpus": item.corpus,
                "category": item.category,
                "difficulty": item.difficulty,
                "ec_tags": item.ec_tags,
                "expected_behaviour": item.expected_behaviour,
                "nl": item.nl,
                "reference_sql": item.reference_sql,
                "sql": (result.get("sql") or {}).get("sql"),
                "row_count": result.get("row_count", 0),
                "rows": (result.get("rows") or [])[:20],
                "verdict": _verdict(verify),
                "caveats": _verify_caveats(verify),
                "wall_ms": wall_ms,
                "stage_latencies_ms": _stage_latencies(events),
                "tokens_per_sec": _tokens_per_sec(events),
                "pipeline_error": result.get("error"),
                **truth_meta,
                **scored,
            }
            records.append(record)

            if reporter:
                reporter.finish_item(record)
            else:
                mark = {"pass": "PASS", "fail": "FAIL", "void": "VOID"}[record["score"]]
                print(
                    f"[{index:>3}/{len(items)}] {item.id:<11} {mark:<4} "
                    f"{record['outcome']:<14} {wall_ms:>6}ms  {record['reason'][:70]}"
                )
    except KeyboardInterrupt:
        header["reportable"] = False
        header["caveats"].append(f"interrupted by the operator after {len(records)} items")
        emit("[interrupted] writing a partial report")
    finally:
        if reporter:
            reporter.close()

    if not records:
        raise SystemExit("No items were run — nothing to report.")

    header["finished_at"] = datetime.now(timezone.utc).isoformat()
    header["items_attempted"] = len(records)
    summary = aggregate(records)
    json_path, md_path = write_reports(header, summary, records)
    return summary, records, json_path, md_path


def print_summary(header: dict, summary: dict, json_path: str, md_path: str) -> None:
    overall = summary["overall"]
    overall_ex = f"{overall['ex']:.1%}" if overall["ex"] is not None else "n/a"
    print("=" * 78)
    print(f"EX overall: {overall['passed']}/{overall['scored']} = {overall_ex}")
    for name, bucket in summary["per_corpus"].items():
        share = f"{bucket['ex']:.1%}" if bucket["ex"] is not None else "—"
        print(f"  {name:<14} {share:>7}  ({bucket['passed']}/{bucket['scored']})")
    for caveat in header["caveats"]:
        print(f"  ! {caveat}")
    print(f"\nReports: {json_path}\n         {md_path}")


# -- main ----------------------------------------------------------------------


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Flags shared with run_benchmarks.py, so the two cannot drift apart."""
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=300, help="per-item HTTP timeout (s)")
    parser.add_argument("--hardware-profile", default="gpu", choices=["gpu", "cpu-only"])
    parser.add_argument("--tag", default="", help="free-text label recorded in the run header")
    parser.add_argument(
        "--minutes", type=float, help="wall-clock budget; stops cleanly when exceeded"
    )
    parser.add_argument(
        "--allow-unfrozen",
        action="store_true",
        help="debug only: run against an unfrozen backend. The report is marked void.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and score a benchmark sweep (§3).")
    parser.add_argument("--corpus", action="append", choices=list(CORPUS_SIZES), default=None)
    parser.add_argument(
        "--profile",
        choices=list(PROFILES),
        help="preset item budget: 30m, 1h, 3h or full (see evaluation/plan.py)",
    )
    parser.add_argument(
        "--total", type=int, help="approximate item budget, allocated proportionally"
    )
    parser.add_argument("--per-corpus", type=int, help="first N items of each corpus")
    parser.add_argument(
        "--rerender",
        metavar="REPORT.json",
        help="recompute a saved run's tables from its stored records and rewrite it in place; "
        "runs nothing and re-scores nothing",
    )
    add_common_arguments(parser)
    args = parser.parse_args()

    if args.rerender:
        json_path, md_path = rerender(args.rerender)
        print(f"Re-rendered from stored records:\n  {json_path}\n  {md_path}")
        return

    corpora = args.corpus or list(CORPUS_SIZES)
    health = preflight(args.base_url, args.allow_unfrozen)
    if args.profile:
        items, selection = plan_run(args.profile, corpora)
    else:
        items, selection = select_items(corpora, args.total, args.per_corpus)
    header = build_header(args.base_url, health, args.hardware_profile, selection, args)
    if args.allow_unfrozen and health.get("freeze_now") != FREEZE_NOW:
        header["reportable"] = False
        header["caveats"].append("§1.1 VOID: executed without the frozen clock")

    print(f"\nScored run — {len(items)} items across {len(corpora)} corpora")
    print(f"  engine   : {header['engine']['description']}")
    print(f"  decoding : greedy={header['decoding']['greedy']} seed={header['decoding']['seed']}")
    print(f"  clock    : {header['freeze_now']}")
    print(f"  selection: {selection['rule']}\n" + "=" * 78)

    summary, _records, json_path, md_path = run_sweep(items, header, args)
    print_summary(header, summary, json_path, md_path)


if __name__ == "__main__":
    main()
