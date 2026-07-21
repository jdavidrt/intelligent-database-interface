# IDI (Intelligent Database Interface) Development Guide

Multi-agent NL2SQL system — a **didactic instrument** that lets anyone query, learn, and understand a real database in plain language.

## Current Status

**Phase 0 (Repo Skeleton & Sandbox Migration): ✅ COMPLETE — 2026-06-26**
**Day 1 (The Agentic Core, DB-less): ✅ COMPLETE — 2026-07-02** — Gate D1 PASSED (6/8 EC probes; EC-07/EC-08 correctly blocked by the syntax-verification layer — fail-safe working as designed). The full seven-agent pipeline runs end-to-end over `/query`, fed entirely by the `soundwave/` files via `SoundwaveFileConnector`.
**Sandbox Detachment: ✅ COMPLETE — 2026-07-02** — the frozen `sandbox/` has been **deleted**. The GGUF model now lives at `models/` (repo root, gitignored) and `llama-server` resolves from winget/PATH. The live frontend chat calls the agentic `/query` pipeline (soundwave-grounded); the legacy `/chat` + `/benchmark` loops build their prompt from the soundwave source files. Nothing in the tree references `sandbox/` anymore.
**REPLAN v2 — 2026-07-02**: sprint order inverted — agents first, physical DB last. Days 1–3 run DB-less on a `SoundwaveFileConnector` (in-memory SQLite built from `soundwave/*.sql`); LoRA *training* is deferred and the hot-swap seam swaps **instruction profiles** (`backend/app/prompts/<agent>.md`) via the same `load_adapter()` API that will later load GGUF adapters.
**Day 2 (Frontend Rebuild & Visualization): ✅ COMPLETE — 2026-07-02** — Gate D2 passed (didactic 4-panel answers, adapter badges, Recharts auto-chart, inline autocomplete, session library + DB-profile drawer, Zustand stores, `styles/tokens.css`, zero Tailwind artifacts). **One known issue pending** (see `DAY2_PLAN.md` §Known Issues, KI-1): restoring a session from `SessionLibrary` loads only the user questions — the assistant answers don't render; the restore path (backend turn persistence and/or `queryStore.loadFromSession` reconstruction) must be improved.
**Multi-Database Restructure: ✅ COMPLETE — 2026-07-03** — `soundwave/` moved to `databases/soundwave/`, the first of what can now be many database folders. `SoundwaveFileConnector` was generalized and renamed `FileConnector` (parameterized by `db_name`, glob-based file discovery — no hardcoded filenames), and a new `backend/app/services/db/discovery.py` dynamically scans `databases/` so dropping in a new database folder needs no code change. The hardcoded soundwave business glossary was extracted from `context_manager.py` into a generic per-DB `NN_<db>_survey.json` convention (`databases/soundwave/04_soundwave_survey.json`). Context is no longer built lazily/accidentally on the first `/query` — the frontend now shows a **database-selection landing screen** before the chat UI (`DatabaseSelector.tsx`), listing databases from a new `GET /db/list` and offering a "use the last database used" shortcut (`GET /db/last-used`, derived from session history); selecting one calls `POST /db/select`, which drives a new explicit `Orchestrator.select_database()` lifecycle method that builds and caches the profile exactly once. The canonical DB identifier is now the folder name (`"soundwave"`, not the old hardcoded `"soundwave_db"`) everywhere — `DBProfile.db_name`, session records, API params. `data/sessions.db` and `data/chromadb/` were cleared as part of this change (both self-heal empty on next backend start).
**Day 3 (Instruction Registry, Hot-Swap Discipline & Evaluation): ✅ COMPLETE — 2026-07-03** — Gate D3 passed. `adapters/registry.json` + `backend/app/services/adapter_registry.py` externalize the agent → instruction-profile mapping; the orchestrator now activates each agent's profile immediately before that agent runs and folds the returned label into that agent's `"started"` `AgentEvent` payload (the frontend needed no changes — `progressStore.ts` already merged `payload.adapter` off any event status). All four `backend/app/prompts/*.md` were expanded into real EC-01…EC-08-tuned specializations. `tests/ab_harness.py` (base-vs-specialized A/B) and `tests/evaluate.py` (execution accuracy hand-derived from the seed data, per-stage latency, tokens/sec) both ship, reusing `gate_d1.py`'s probes/streaming client — both require a live backend to actually run and are left for manual execution. A 24-test `pytest` suite runs fully offline (LLM/vector calls mocked at each agent's import site) — first-ever `pyproject.toml` (`ruff`/`black`) and frontend `eslint.config.js`/`.prettierrc.json` also landed this day. See `DAY3_PLAN.md`'s completion note for the two small as-built additions (`llm_service.chat_with_meta()` for tokens/sec; a data quirk found in EC-08's probe, where the referenced artist "Adele" doesn't exist in soundwave_db, so its correct answer is 0 rows).
**Schema Grounding ("closed join vocabulary"): ✅ COMPLETE — 2026-07-19** — born from a real failure ("most reproduced artists of the last year" generated the nonexistent `play_events.artist_id` join). New `backend/app/services/db/join_graph.py` resolves multi-hop FK chains deterministically (union-find column equivalence classes make transitive joins like `track_artists.track_id = play_events.track_id` legal; junction-table preference picks the EC-08 bridge route over the albums route). The SQL Generator now (a) runs an optional constrained-decoding plan step (`IDI_CONSTRAINED_PLANNING`, default on — llama.cpp `response_format` json_schema whose enums are exactly the schema's tables/edges/columns, compiled to GBNF so out-of-vocabulary identifiers are unsamplable; join edges then recomputed deterministically via `join_tree`), and (b) falls back to injecting a deterministic "Precomputed join plan" when the plan step is unavailable. The verifier's semantic layer now enforces prompt rule 4b: every JOIN ON equality must be a (transitively) legal FK edge, with the legal chain named in the rejection message for the regeneration loop. Also fixed en passant: `_mysql_to_sqlite` didn't recurse into rewritten `DATE_SUB`/`DATE_ADD` arguments, so an inner `CURDATE()` rendered as SQLite's `CURRENT_DATE` and ignored `IDI_FREEZE_NOW`. 13 new offline tests in `tests/test_schema_grounding.py` (101 total green).
**Interlude — Vocabulary Parity & Verifier False Positives ("one vocabulary, three callers"): ✅ COMPLETE — 2026-07-20** — Step 0 of `SQL_HARDENING_PLAN.md`. The three parties that consult the closed join vocabulary — the prompt (`_build_schema_summary`), the planner (`JoinGraph.join_tree`) and the verifier (rule 4b) — disagreed with each other, and the verifier rejected legal SQL. Fixed, each reproduced against the live profile first: self-referencing FKs no longer merge union-find classes (they made `payments.user_id = users.referred_by_user_id` "legal" and routed `playlists→tracks` through the fork-lineage column; 11 of 86 edges were poisoned, now 75); `_edge_label` prefers a real FK over a derived shortcut; the prompt no longer calls its 29-FK list exhaustive while the plan ships one of the 46 derived equalities, which are now annotated as shortcuts (`_render_join_edges`). Five verifier false positives removed: CTE names were checked against the schema table list, an ON clause carrying a filter alongside its key (`ON al.artist_id = a.artist_id AND al.label = a.label`) was rejected as an invented join key, and the aggregate-in-WHERE **regex** rejected legal single-line SQL (`WHERE … HAVING COUNT(*)`) — now a scope-limited AST walk, since the naive version flags legal `WHERE x IN (SELECT … HAVING COUNT(*))`. Rule 4b now checks per-JOIN *anchoring* (at least one legal equality) instead of per-equality. Two holes closed: implicit comma joins bypassed rule 4b entirely, and the read-only guard was duplicated in `_layer_sanity` and `FileConnector.execute_read` with both copies wrong in both directions (rejected every `WITH … SELECT`, passed `SELECT 1; DROP TABLE users`) — now one shared `services/sql_safety.py:is_read_only()`, AST-based, failing closed. Alias handling (`FROM artists AS a` → `a.name`) was already correct and is now pinned with regressions plus a "never fix this with a regex" comment. New `tests/test_vocabulary_parity.py` (invariants V0–V2 as properties over every 2- and 3-table combination) and `tests/test_verification_false_positives.py` (14-entry legal-SQL corpus, asserted per layer, end-to-end, and actually executing, paired with 9 must-reject cases). **104 → 177 tests green.** Steps 1–6 of that plan (greedy sampling, structured SQL emission, A/B) remain pending.
**Third verdict — "possibly right" (`caution`): ✅ COMPLETE — 2026-07-21** — some queries are neither right nor wrong until you know what the user meant, so `VerifyReport.verdict` is now `pass` / `caution` / `fail`. **A caveat never blocks**: `overall_passed` stays `True`, the query executes, and the caveat rides into the didactic answer (this is the load-bearing invariant, pinned by test). Four sources, all previously *silent* passes: ambiguous junction bridge (`playlists→tracks` via `playlist_tracks` vs `play_events` — the FK graph's tie-break was a coin-flip), self-join direction (the graph knows tables, not roles), join sides that resolve to no schema table (CTE/subquery/outer alias), and an extra key-column equality alongside a real FK (`is_key_column` is the discriminator, so it never fires on legal filter-in-`ON`). `JoinGraph.ambiguous_bridges()` exposes the ties; a new per-DB survey key `join_preferences` lets a human settle a route where the domain has one right answer — seeded with exactly one entry (the EC-08 bridge), leaving `playlists↔tracks` deliberately ambiguous. Two adjacent fixes: `tests/conftest.py:soundwave_profile` now mirrors `ContextManager` (it built a survey-less profile production never uses, so glossary/coded-values/join-preferences were empty in tests only — production was always correct), and survey `_comment` keys no longer reach the profile as real domain knowledge (they feed the SQL Generator's prompt via `glossary`). **177 → 208 tests green.** Known issues and caveats are catalogued in `SQL_HARDENING_PLAN.md` §"Known issues & caveats" and in the report's §3.12.6.
**Evaluation Corpora (Chapter 4 §4.1): ✅ COMPLETE — 2026-07-21** — `docs/EVALUATION_PROTOCOL.md` §2 discharged. All four corpora authored and frozen under `data/benchmarks/corpora/` (**225 items**: spider_style 60, bird_style 60, soundwave_30 30, idi_exec_75 75), every one executing against SoundWave under the frozen clock — the protocol derives ground truth by execution (§3.1), so a DB without data cannot host a corpus, and the idea of separate Spider/BIRD schemas was dropped for that reason. New top-level `evaluation/` package: `hardness.py` ports Spider's `evaluation.py::eval_hardness` so **tiers are computed from the reference SQL, never declared** (§2.1) — the builders refuse to write a manifest when a computed tier disagrees with the authored intent; `corpus.py` holds the §2.2 schema and conformance checks; `validate.py` is a pre-run gate; `transcribe_soundwave.py` parses Q01–Q30 out of the syllabus so that census provably matches its source. BIRD and IDI-EXEC tiers are computed through declared mappings (`BIRD_FROM_SPIDER`, `EXEC_FROM_SPIDER`) since neither has a mechanical definition of its own — a documented trade of fidelity for falsifiability. **Protocol raised to v1.2** with seven defects fixed and logged in §11, the substantive one being EC-07: the schema, protocol and DB documentation all claimed `daily_artist_metrics.stream_count` ran "~5% above" `COUNT(play_events)`, but that was design intent the seed generator never produced — measured, it is **290,000×–1,070,000×** (The Weeknd: 225 raw plays vs 65,314,971), because the cached columns are seeded at production scale against a ~1,000-row event log. At that spread §9 quirk 2's old remedy (list both sources in `accepted_alternatives`) made an item unfalsifiable, so the rule inverted: EC-07 items must name their source and `accepted_alternatives` is forbidden on them. Also corrected: §8.3's sampling allocation and §2.1's "20 of the 30" (both stale against the v1.1 corpus sizes), §5's latency set (said "the 10 easy-tier items" of a 24-item tier — an unpinned degree of freedom), §1.1's payment total (421 → 442), one demonstrably wrong reference query (Q22's `COUNT(*)` after a LEFT JOIN counted 963 events as 48 tracks), and `00_soundwave_db_documentation.md`'s row-count table, which still described the pre-extension dataset. `tests/evaluate.py` gained an EC-07 checker — the probe had been left unscored on the premise that the data was "frozen at 2025-01-20", which the v1.1 extension invalidated. **208 → 229 tests green** (`tests/test_corpora.py`, fully offline).
Active phase: **Day 4 — Real DB Connection & Hardening** (per the replanned order below).
New order: D1 agents → D2 frontend → D3 instruction registry + evaluation → D4 real MySQL connection.
See `MASTERPLAN.md` for the full plan; v1 day plans are archived in `legacydocs/DAY*_PLAN_v1.md` and remain the code reference for carried-over steps.

## Active Documentation

| Doc | Purpose |
|---|---|
| `MASTERPLAN.md` | Single source of truth: architecture, agent contracts, day-by-day plan |
| `CLAUDE.md` | This file — dev guidelines & assistant orientation |
| `docs/TECHNOLOGY_DEEP_DIVE.md` | Deep dives on ChromaDB, SQLite, Recharts, LoRA, WebSockets, GGUF |
| `databases/soundwave/02_soundwave_context.md` | DB domain context (schema narrative, business rules) |
| `databases/soundwave/03_soundwave_edge_cases.md` | EC-01…EC-08 edge-case taxonomy — the verification test syllabus |
| `docs/EVALUATION_PROTOCOL.md` | Chapter 4 §4.1 — frozen metrics, corpora and scoring rules. Read §0.2 before changing anything in it |
| `data/benchmarks/README.md` | Where the four frozen corpora live, how to regenerate/verify them, and the run presets |

> Older docs (pre-plan briefs, SRS placeholder, proposals) are in `legacydocs/` — not relevant to active development.

## Strategic Project Context

### Purpose & Audience
- **Target User**: Learner, analyst, or newcomer to a real database.
- **Goal**: Lower the barrier to understanding data and SQL — every answer doubles as a guided lesson.
- **Value Proposition**: The system teaches the database while it answers.

### Guiding Principles
- **Local-First over Cloud**: Prioritize local execution to minimize costs and protect sensitive data.
- **Didactic-First UX**: Every agent has a teaching obligation — surface what it understood, what it queried, and why.
- **Fail-Safe Design**: Never execute unverified SQL; mandatory three-layer verification chain (Syntax → Semantic → Sanity).
- **Hard-Constraint targets**: Consumer-grade hardware (16 GB RAM, 4 GB VRAM / GTX 1650 class). VRAM budget < 3.5 GB with an active adapter.

### 🤖 Multi-Agent Ecosystem
The system orchestrates seven specialized modules:
1. **Context Manager**: Domain knowledge & surveys.
2. **Query Understanding**: Intent parsing & ambiguity detection.
3. **SQL Generator**: NL2SQL translation (LoRA adapters).
4. **Verification Agent**: The correctness gatekeeper.
5. **Visualization Engine**: Intelligent chart selection.
6. **Session Manager**: Context & continuity.
7. **Orchestrator**: Dynamic workflow routing.

## Build and Run Commands

### Backend (FastAPI)
- **Install dependencies**: `pip install -r backend/requirements.txt`
- **Run all (recommended)**: `python start.py` from workspace root (launches llama.cpp + FastAPI + Vite)
- **Run dev server alone**: `uvicorn backend.app.main:app --reload` (from workspace root)
- **Run llama.cpp server**: install the binary with `winget install ggml.llamacpp` (or put `llama-server` on PATH), place the GGUF at `models/qwen2.5-coder-3b-instruct-q4_k_m.gguf`, then run `llama-server --model models/qwen2.5-coder-3b-instruct-q4_k_m.gguf --port 7860 -ngl 99`. `start.py` does this automatically.

### Frontend (React)
- **Install dependencies**: `npm install` (in `frontend` directory)
- **Run dev server**: `npm run dev`
- **Build production**: `npm run build`

## Test Commands
- **Backend tests**: `pytest tests/` (from workspace root)
- **Frontend tests**: `npm test` (in `frontend` directory)
- **Benchmarks**: `python run_benchmarks.py` (from workspace root, backend must be running) — menu of
  30m / 1h / 3h / full presets over the four frozen corpora, with live progress. Only `full` is
  reportable as a §3 corpus EX; see `data/benchmarks/README.md`.

## Code Style & Standards

### Python (Backend)
- **Linting/Formatting**: Use `ruff` and `black`.
- **Command**: `ruff check .` or `black .`
- **Typing**: Strict type hints required for all agent boundaries and API endpoints.

### TypeScript/React (Frontend)
- **Framework**: React 18+ with TypeScript and Zustand.
- **Styling**: CSS Modules + design tokens (`styles/tokens.css`). No Tailwind, no shadcn/ui — locked per MASTERPLAN.md D1.
- **Design Aesthetic**: High-density, glass-themed, premium look-and-feel.

## Assistant Orientation
- **Minimize Dependencies**: Avoid adding new heavy libraries; leverage existing tech stack.
- **Functional Modularity**: Keep agents decoupled; changes in one should not break the orchestration logic.
- **Performance Aware**: Be mindful of VRAM usage; assume the 4GB limit for the inference engine.
- **Verification Priority**: When implementing features, always consider how they will be verified (both automated and via the Verification Agent).
