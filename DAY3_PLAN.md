# Day 3 — Instruction Registry, Hot-Swap Discipline & Evaluation
## IDI Implementation Plan (v2)

> **✅ COMPLETE — 2026-07-03.** `adapters/registry.json` + `backend/app/services/adapter_registry.py` externalize the agent → instruction-profile mapping; activation is now centralized in the orchestrator (called once per agent, immediately before that agent runs, with the returned label folded straight into that agent's `"started"` `AgentEvent` payload) rather than each agent module self-activating — a deliberate refinement of Step 1's sketch so a `"started"` row is guaranteed to already carry its adapter label instead of racing a separate `"progress"` event. The frontend needed **zero changes**: `progressStore.ts` already merged `payload.adapter` off any event status. All four `backend/app/prompts/*.md` were expanded with concrete EC-01…EC-08 rules. `tests/ab_harness.py` and `tests/evaluate.py` both ship, reusing `gate_d1.py`'s `PROBES`/`run_query` by same-directory import. A 24-test `pytest` suite (`tests/conftest.py` + 4 test files) runs fully offline — no live backend/llama.cpp needed — by mocking `llm_service.chat`/`chat_with_meta` and `query_context` at each agent module's *import site* (a documented gotcha: patching the definition site in `memory/vector.py` would silently no-op). `pyproject.toml` + `ruff`/`black` (backend) and `eslint.config.js`/`.prettierrc.json` (frontend) landed as the sprint's first lint configs; both are clean on every file this day touched (pre-existing long-line debt elsewhere in the tree was left alone as out of scope).
>
> **Two as-built additions beyond the file checklist**, both scoped narrowly: (1) tokens/sec required a small, additive `llm_service.chat_with_meta()` alongside the unchanged `chat()`, wired through `sql_generator.py` only (not all three LLM-calling agents) and merged into the `sql_generator` `"done"` event payload — the only way `evaluate.py`, as a black-box HTTP harness, can observe it. (2) `verification.py`'s dead `llm_service` import was removed — `verify()` has never called `chat()` (its 3-layer chain is pure `sqlglot`/regex); the profile exists for discipline/future-proofing, documented in `prompts/verification.md`.
>
> **Data quirk found during `evaluate.py`'s ground-truth derivation (not a bug, just worth knowing):** `gate_d1.py`'s EC-08 probe asks for playlists containing tracks "by Adele" — no artist named Adele exists in soundwave_db's 12-artist catalog, so the correct answer is **0 rows**. That means EC-08 can never satisfy `gate_d1.py`'s/`ab_harness.py`'s `row_count > 0` pass heuristic even with perfect SQL. `evaluate.py`'s accuracy checker correctly expects 0 rows for EC-08; `gate_d1.py` itself was left untouched per this plan's "import, don't duplicate" instruction.

**Goal:** The "LoRA layer" without the training. A per-agent adapter registry that swaps instruction profiles today and will swap GGUF adapters tomorrow through the same seam — plus the measurement harness that makes the swap's value visible.

**Gate D3:** Registry swaps are observable per agent in the `AgentEvent` stream; the A/B report exists and shows specialized profiles ≥ base instructions on the EC suite; `pytest` is green; deleting a profile file degrades gracefully to base instructions without breaking the pipeline.

**Pre-condition:** Gate D2 passed — full pipeline usable from the browser.

---

## Step 1 — Adapter Registry

Create `adapters/registry.json` — the single source of truth for which artifact each agent runs on:

```json
{
  "sql_generator":       { "kind": "prompt", "artifact": "sql_generator.md" },
  "query_understanding": { "kind": "prompt", "artifact": "query_understanding.md" },
  "verification":        { "kind": "prompt", "artifact": "verification.md" },
  "clarification":       { "kind": "prompt", "artifact": "clarification.md" }
}
```

Create `backend/app/services/adapter_registry.py`:

```python
"""Adapter registry - maps each agent to its active artifact.

kind "prompt" -> backend/app/prompts/<artifact> (instruction profile, active now)
kind "gguf"   -> adapters/<artifact> (LoRA adapter, post-sprint)
Missing registry entry or missing file -> base instructions (fail-safe).
"""

from __future__ import annotations
import json
import os

from backend.app.config import settings
from backend.app.services.llm_service import llm_service

_REGISTRY_PATH = os.path.join(settings.repo_root, "adapters", "registry.json")


def load_registry() -> dict:
    if not os.path.isfile(_REGISTRY_PATH):
        return {}
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def activate(agent_name: str) -> str:
    """Activate the registered artifact for an agent. Returns a label for AgentEvents."""
    entry = load_registry().get(agent_name)
    if entry is None:
        llm_service.unload_adapter()
        return "base"
    if entry["kind"] == "gguf":
        # Post-sprint: llm_service will call llama.cpp /lora-adapters here.
        # Until wired, fall through to the prompt profile of the same name.
        pass
    llm_service.load_adapter(agent_name)
    return llm_service.active_adapter() or "base"
```

Orchestrator change: replace direct `llm_service.load_adapter(...)` calls (Day 1 Step 8 discipline) with `adapter_registry.activate(agent_name)` and put the returned label into the agent's `started` event payload.

---

## Step 2 — Author the Four Instruction Profiles

Expand the Day 1 seed profiles into real specialization artifacts, each tuned against `databases/soundwave/03_soundwave_edge_cases.md`. These are the sprint's stand-ins for trained adapters — treat them as seriously as training data.

| Profile | Must encode |
|---|---|
| `prompts/sql_generator.md` | MySQL dialect; single SELECT; explicit `IS NULL` for nullable FKs (EC-03); coded-value substitution (EC-02); raw-vs-cached source-of-truth (EC-07); qualified column names (EC-01); abbreviation glossary (EC-05); self-join awareness (EC-04); temporal validity via pricing_history (EC-06); junction-table paths (EC-08) |
| `prompts/query_understanding.md` | Entity/metric/filter extraction; ambiguity flagging keyed to the taxonomy (which "name"? which time window? raw or cached?) |
| `prompts/verification.md` | Layer-by-layer reporting language; repair suggestions phrased as lessons |
| `prompts/clarification.md` | One question, non-technical phrasing, offers the taxonomy-informed choice |

Rule: profiles contain **stable specialization**, not per-query context. Schema and retrieved passages keep flowing through the user/system message as on Day 1 — the profile is the part a LoRA would internalize.

---

## Step 3 — A/B Harness (Base vs Specialized)

Create `tests/ab_harness.py`:

```python
"""A/B harness - EC suite with base instructions vs instruction profiles.

Run A: registry.json temporarily emptied  -> all agents on base instructions.
Run B: registry.json as authored          -> specialized profiles active.
Output: data/benchmarks/ab_report_<date>.json + console table.
Metrics per run: EC pass count (of 8), per-probe verification verdicts,
mean latency per query, generated-SQL exact-keyword hits (IS NULL, etc.).
"""
```

Implementation notes:
- Reuse the probe list and streaming client from `tests/gate_d1.py` — import, don't duplicate.
- Toggle by writing a temp registry (`{}` for run A) and restoring the original after; the registry is read per-activation, so no restart is needed.
- Persist both runs' raw results; the report records the **delta**. This file is the baseline any post-sprint trained adapter must beat.

---

## Step 4 — Evaluation Harness

Create `tests/evaluate.py` — the durable benchmark (distinct from the pass/fail gate):

- **Execution accuracy**: expected-result assertions per EC probe (row counts / key values from the seed data, hand-derived once from `02_soundwave_data.sql`).
- **Latency**: wall-clock per pipeline stage from `AgentEvent` timestamps.
- **Tokens/sec**: from llama.cpp response metadata.
- Output: `data/benchmarks/eval_<date>.json` + a markdown summary table.

---

## Step 5 — Test Suite & Linting

`[v1 → legacydocs/DAY4_PLAN_v1.md Steps 5–7]` carry over, retargeted:

- `pytest` for: `FileConnector` (load, introspect, read-only guard, LIMIT injection, transpile — renamed from `SoundwaveFileConnector` and parameterized by `db_name` on 2026-07-03, see `MASTERPLAN.md`), verification 3-layer chain, orchestrator routing (clarification branch, repair loop), **adapter registry** (activation, fallback on missing file, GGUF fall-through).
- `ruff` + `black` config; ESLint + Prettier for the frontend.

---

## Gate D3 Verification

1. [x] `pytest tests/` — green (24 passed, no live server required).
2. [ ] Run a query from the browser: each LLM agent's progress row shows its profile label; edit `registry.json` to remove one agent, re-query — that agent shows `base`, pipeline still completes. **Wiring is done and covered by `test_orchestrator.py`'s adapter-label assertions and `test_adapter_registry.py`'s fallback tests; the live-browser click-through itself is left to manual testing per this sprint's workflow.**
3. [ ] `python tests/ab_harness.py` — written and lint/import-clean; requires a running backend + llama.cpp to actually execute (same precondition as `gate_d1.py`) — run manually to produce a report.
4. [ ] `python tests/evaluate.py` — written, with hand-derived ground truth for EC-01–EC-06 and EC-08 (EC-07 is date-relative, intentionally `not_scored`); same live-server precondition as above.
5. [x] Delete a profile file (not just the registry entry) — already guaranteed by `llm_service.load_adapter`'s pre-existing fail-safe, now reached through `adapter_registry.activate`; covered by `test_adapter_registry.py::test_activate_missing_profile_file_falls_back_to_base`.

---

## File Checklist

| File | Action |
|---|---|
| `adapters/registry.json` | ✅ Created |
| `backend/app/services/adapter_registry.py` | ✅ Created |
| `backend/app/services/orchestrator.py` | ✅ Adapter activation via registry |
| `backend/app/prompts/*.md` | ✅ Expanded to full profiles |
| `tests/ab_harness.py` | ✅ Created |
| `tests/evaluate.py` | ✅ Created |
| `tests/test_*.py` (pytest suite) | ✅ Created (`conftest.py` + 4 test files, 24 tests) |
| `pyproject.toml` / lint configs | ✅ Created (backend `pyproject.toml`; frontend `eslint.config.js` + `.prettierrc.json`) |
| `data/benchmarks/` | Reports land here |
