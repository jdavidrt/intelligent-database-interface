# IDI — 4-Day Implementation Masterplan

**From single-prompt prototype to multi-agent didactic NL2SQL engine.**

Universidad Nacional de Colombia — Computer and Systems Engineering Thesis — 2026
Author: Juan David Ramírez Torres (`jdramirezt@unal.edu.co`)
Plan window: a **Day 0** prep step (repo skeleton + sandbox migration) followed by 4 working days. Domain context lives under `databases/<db_name>/` — e.g. `databases/soundwave/` (`02_soundwave_context.md`, `03_soundwave_edge_cases.md`).

> **REPLAN v2 — 2026-07-02.** The sprint order was inverted to put the agentic architecture first and the physical database last. The real MySQL connection and LoRA *training* are deferred; the system boots entirely from the `soundwave/` files (schema SQL, seed data, context, edge cases) and hot-swaps **per-agent instruction profiles** through the same interface that will later hot-swap GGUF adapters. New order: **agents → frontend → instruction/adapter layer + evaluation → real DB connection**. The v1 day plans are archived in `legacydocs/DAY*_PLAN_v1.md`; code blocks there are still the implementation reference wherever a step carries over.

> **Multi-Database Restructure — 2026-07-03.** `soundwave/` moved under `databases/soundwave/`, the first of what can now be many database folders — `GET /db/list` discovers them dynamically, so a new folder needs no code change. `SoundwaveFileConnector` was generalized and renamed **`FileConnector(db_name)`** (glob-based `*_schema.sql`/`*_data.sql` discovery instead of hardcoded filenames); the hardcoded soundwave glossary moved out of `context_manager.py` into a generic per-database `NN_<db_name>_survey.json` convention (`databases/soundwave/04_soundwave_survey.json`). Context is no longer built lazily on the first `/query` — a new frontend landing screen (`DatabaseSelector.tsx`) makes selection explicit, calling `POST /db/select`, which drives a new `Orchestrator.select_database()` lifecycle method that builds and caches the profile exactly once (plus a "use the last database used" shortcut off `GET /db/last-used`, derived from session history). The canonical DB identifier is now the folder name (`soundwave`, not the old hardcoded `soundwave_db`) everywhere — `DBProfile.db_name`, session records, API params. Session history and the ChromaDB cache were reset as part of this change (both self-heal empty on next backend start). Class names, paths, and the architecture references below (§3, §6, §12) have been updated to match; the rest of this plan's day-by-day narrative is left as written at the time it was authored.

---

## 0. The Reframe — What IDI Is Now

IDI is no longer pitched as an *executive decision ally*. It is reframed as a **didactic instrument**: a tool that, when plugged into a real database, brings data engineering, data intelligence, and SQL within reach of anyone who wants to **learn** a database, **understand** one they inherited, or simply **run an analysis** without a technical intermediary and with a simple statistical insights.

| Dimension | Old framing (brief) | New framing (this plan) |
|---|---|---|
| Primary user | Non-technical executive | Learner / analyst / curious newcomer to a real DB |
| Core value | Reduce decision latency | Lower the barrier to understanding data and SQL |
| Output | A verified answer | A verified answer **plus a transparent lesson** (why this schema, why these joins, why this edge case matters) |
| Differentiator | Business insight automation | The system *teaches the database* while it answers |
| Why soundwave fits | Realistic business domain | A deliberate **edge-case taxonomy** (EC-01…EC-08) — a built-in syllabus of how SQL goes wrong |

The didactic reframe is not cosmetic. Every agent gains a **teaching obligation**: the orchestrator must surface *what it understood, what it queried, and why* in plain language, so the answer doubles as a guided reading of the database.

---

## 1. Scope Decisions (Locked)

These four decisions were confirmed before planning and are now binding. They are recorded here ADR-style so the rationale survives the sprint.

| # | Decision | Choice | Consequence |
|---|---|---|---|
| D1 | Styling layer | **CSS with classes, CSS Modules + design tokens.** Tailwind removed entirely; shadcn/ui dropped with it (it depends on Tailwind). | Zero utility-framework build dependency. We port the existing glass theme from `sandbox/.../index.css` into tokenized CSS Modules and a small in-house component kit. |
| D2 *(amended v2)* | LoRA training | **Deferred past the sprint.** The hot-swap *mechanism* ships now, but what it swaps are **instruction profiles** (per-agent system prompts) instead of trained adapters. Colab + Unsloth training happens post-sprint through the same seam. | `LLMService.load_adapter(name)` keeps its signature; today it activates `prompts/<name>.md`, tomorrow it activates `adapters/<name>.gguf` when the file exists. Nothing downstream changes. |
| D3 *(amended v2)* | DB connectivity | **File-first, MySQL last.** Days 1–3 run on a **`FileConnector`** *(generalized/renamed from `SoundwaveFileConnector` on 2026-07-03)* — an in-memory SQLite built from `databases/<db_name>/…schema.sql` + `…data.sql` (transpiled MySQL→SQLite via sqlglot). `MySQLConnector` lands on Day 4 behind the same `DBConnector` interface. | Zero DB setup blocks the agentic work; execution still returns real rows from the seed data, so gates stay honest. Connector choice is one config flag. |
| D4 | Agent depth | **Full seven agents from the brief.** | Maximum thesis fidelity. Mitigated by reusing the working sandbox loop as the SQL-generation fallback so nothing regresses while agents are built. |
| D5 *(new v2)* | Context source | **Each `databases/<db_name>/` folder is a context feed, discovered dynamically** *(`GET /db/list`, added 2026-07-03)*; `soundwave` is the only one populated until Day 4. Auto-exploration = parse `…schema.sql` into `DBProfile` (tables, columns, FKs) + ingest the folder's context/edge-case markdown into ChromaDB. | `DBProfile` has the exact same shape as live introspection would produce, so the Day 4 swap to `information_schema` is invisible to every agent. |

> Note on D1: the working sandbox **never actually used Tailwind** — it already ships raw CSS. "Eliminating Tailwind completely" therefore means closing that door in the brief, the stubs, and any future scaffold, and committing to the CSS-Modules-plus-tokens path.

---

## 2. Hard Constraints (Carried From CLAUDE.md)

- **Local-first inference**: Qwen2.5-Coder-3B-Instruct (Q4_K_M, GGUF) on llama.cpp, consumer hardware (16 GB RAM, 4 GB VRAM / GTX 1650 class). VRAM budget < 3.5 GB with an active adapter.
- **Fail-safe**: never execute unverified SQL. Three-layer chain (Syntax → Semantic → Sanity) is mandatory before any execution against soundwave.
- **Minimize dependencies**: no heavy new libraries; lean on the existing stack.
- **Verification priority**: every feature ships with a way to verify it (automated test and/or the Verification Agent).
- **Code language**: all code and comments in English. Windows + VSCode is the reference dev environment.

---

## 3. Target Architecture

The seven modules sit behind one FastAPI process; the orchestrator drives a deterministic pipeline with dynamic branches (clarification, retry-on-verify-fail). The LLM Service is the single point that talks to llama.cpp and owns LoRA hot-swap.

```
React Frontend (CSS Modules + tokens, Zustand, Recharts)
   InputArea(+autocomplete)  AnswerPanel(4 didactic panels)  Visualization
   AgentProgress(+adapter badge)  SessionLibrary  DBProfileForm (read-only)
        │  REST + NDJSON stream (per-agent progress; /ws live but unwired — Day 2 Delta 0)
        ▼
FastAPI Backend
   Orchestrator  ──drives──▶  [1 Context Mgr] [2 Query Understanding]
                              [3 SQL Generator] [4 Verification]
                              [5 Visualization] [6 Session Manager]
        │                              │
        ▼                              ▼
   LLM Service (adapter controller)   DBConnector (thin interface)
   • instruction hot-swap NOW         • FileConnector (Days 1–3, one per
     (prompts/<agent>.md)               databases/<db_name>/): in-memory
   • GGUF hot-swap LATER (same API)     SQLite from that folder's *.sql
   • base-model fallback              • MySQLConnector (Day 4) → soundwave_db
                                       • introspection + read-only execution
        │                              │
        ▼                              ▼
   llama.cpp (Qwen2.5-Coder-3B)   ChromaDB (context)   SQLite (sessions)
   + instruction profiles now, LoRA adapters (GGUF) post-sprint
```

### Canonical repository layout (target end-state)

```
backend/
  app/
    main.py                 # FastAPI entry
    config.py               # settings (ports, paths, DB DSN)
    api/routes/             # query.py  session.py  health.py  db.py
    api/websocket.py        # per-agent progress stream
    services/
      llm_service.py        # llama.cpp + LoRA hot-swap + fallback
      orchestrator.py       # 7-agent workflow routing + state
      sql_executor.py       # read-only execution via DBConnector
      db/connector.py       # DBConnector protocol (thin interface)
      db/mysql_connector.py # soundwave implementation
      memory/sessions.py    # SQLite persistence
      memory/vector.py      # ChromaDB context store
    agents/
      context_manager.py  query_understanding.py  sql_generator.py
      verification.py     visualization.py        clarification.py
    prompts/                # one template per agent
frontend/
  src/
    components/ AnswerPanel  Visualization  AgentProgress  InputArea(+autocomplete)
                SessionLibrary  DBProfileForm  Drawer  ResultsTable  (+ chat MVP carryovers)
    styles/ tokens.css + per-component *.module.css
    stores/                 # Zustand: query, session, dbProfile, progress
    services/ api.ts        # NDJSON stream + REST fetchers (no ws.ts — Day 2 Delta 0)
adapters/                   # *.gguf pulled from Colab
training/                   # Colab notebooks + data prep + lora_config
data/ benchmarks/ synthetic/
databases/soundwave/        # schema + data + edge cases + survey (one DB folder; more can be added)
tests/                      # pytest + frontend tests
deployment/                 # Dockerfile + docker-compose
```

> Today the only living code is in `sandbox/`; the top-level `backend/*.py` and `training/*.py` are 0-byte stubs (plus a stray Flask `backend/app.py` from an earlier attempt). **Day 0** copies the working sandbox loop into this layout — preserving the proven chat path as a fallback in a frozen `sandbox/` — so Day 1 starts from a running canonical skeleton rather than a restructure.

---

## 4. The Seven Agents — IO Contracts

Each agent is a pure-ish function over a shared, typed envelope (Pydantic). Keeping the contracts narrow is what lets seven modules coexist without tangling the orchestrator.

| # | Agent | Input | Output | LoRA | Teaching obligation |
|---|---|---|---|---|---|
| 1 | **Context Manager** | DB connection + characterization survey | `DBProfile` (schema graph, glossary, coded-value maps, embeddings) | none | Produces the "DB profile card" the learner reads |
| 2 | **Query Understanding** | user text + `DBProfile` | `Intent` (entities, metrics, filters, ambiguity flags) | `query_understanding.gguf` | States, in plain words, *what it thinks you asked* |
| 3 | **Clarification** | `Intent` with ambiguity flags | follow-up question(s) | `clarification.gguf` (optional) | Turns ambiguity into a teachable choice |
| 4 | **SQL Generator** | `Intent` + `DBProfile` | candidate SQL + rationale | `sql_generator.gguf` | Explains the join path and table choice |
| 5 | **Verification** | candidate SQL + `DBProfile` | verdict + repaired SQL + per-layer report | `verification.gguf` | Shows *which* of the 3 layers caught what |
| 6 | **Visualization** | result set schema | chart spec (Recharts) | none | Explains why this chart fits this shape |
| 7 | **Orchestrator** | everything | routed workflow + progress events + final answer | none | Assembles the transparent lesson |

> Session Manager is cross-cutting (persistence + multi-turn memory), wired into the orchestrator rather than placed in the linear pipeline.

### The three-layer verification chain (non-negotiable)

| Layer | Question | Mechanism (local, cheap) |
|---|---|---|
| Syntax | Is it valid SQL? | `sqlglot` parse + MySQL `EXPLAIN` (no execution) |
| Semantic | Do tables/columns exist and link correctly? | schema-linking against `DBProfile`; reject hallucinated names |
| Sanity | Is the result plausible and safe? | read-only guard, forced `LIMIT`, dry-run row-count, NULL/`= NULL` and pre-agg-vs-raw heuristics from the soundwave taxonomy |

---

## 5. Day-by-Day Plan

Each day ends with a **verification gate** — a concrete, failable check. **v2 order**: agents first (the thesis contribution), then the didactic frontend, then the adapter/instruction layer with its evaluation harness, and the physical database last — arriving behind an interface nothing above it can distinguish from the files it replaces.

### Day 0 — Repo Skeleton & Sandbox Migration *(pre-sprint)* ✅ COMPLETE — 2026-06-26

> **Post-migration update (2026-07-02):** the frozen `sandbox/` has since been **removed**. The
> canonical backend no longer depends on it: the GGUF model now lives at `models/` (repo root,
> gitignored) and `llama-server` is resolved from winget/PATH. The live frontend chat now calls the
> agentic `/query` pipeline (grounded in `databases/soundwave/`), and the legacy `/chat` + `/benchmark` loops
> build their prompt from the soundwave source files. The historical Day-0 record below is kept for
> context; references to `sandbox/…` describe the state at migration time, not the current tree.

*Goal: stand up the canonical layout and prove the sandbox loop runs unchanged from its new home — with `sandbox/` frozen as a known-good fallback.*

This is the structural foundation the sprint builds on (your explicit priority: *"empecemos por las tareas más fundamentales para darle estructura al proyecto"*). No new behavior is added: the proven sandbox chat loop is **copied** into the canonical paths and must answer a query identically from there. `sandbox/` is left untouched as the reference implementation and runtime fallback.

- [x] Scaffold the full canonical tree from §3 (`backend/app/...`, `frontend/src/...`, `adapters/`, `training/`, `data/`, `tests/`, `deployment/`) with package markers (`__init__.py`) and short placeholder `README`s in otherwise-empty dirs.
- [x] Copy the working sandbox into canonical paths per the migration map below — **copy, not move**; `sandbox/` stays frozen.
- [x] Resolve the top-level conflicts: delete the stray Flask `backend/app.py` (superseded by the FastAPI loop) and clear the 0-byte stubs that collide with copied files; keep a stub only where it marks a genuine Day-1+ target.
- [x] Port `sandbox/start.py` to a root-level `start.py` that launches llama.cpp + backend + frontend from the **canonical** paths (binary and model located as today; the heavy `llama.cpp/` build is referenced in place, not copied).
- [x] Smoke-test the migrated tree end-to-end.

**Gate D0**: ✅ PASSED — `python start.py` brings up llama.cpp + canonical FastAPI backend + canonical Vite frontend from the canonical paths. `sandbox/` still runs independently via `python sandbox/start.py`.

**Migration map:**

| Sandbox source (frozen) | Canonical destination | Note |
|---|---|---|
| `sandbox/backend/main.py` | `backend/app/main.py` | FastAPI entry; the proven chat loop becomes the SQL fallback Day 1 wraps |
| `sandbox/backend/requirements.txt` | `backend/requirements.txt` | dependency baseline |
| `sandbox/frontend/src/` (App, components, utils, `index.css`) | `frontend/src/` | `sqlHighlighter.ts` / `markdownRenderer.ts` carried forward verbatim |
| `sandbox/frontend/{index.html, package.json, vite.config.ts, tsconfig.json}` | `frontend/` | build config |
| `sandbox/context/` (`DB_context.md`, `SYSTEM_PROMPT.md`) | `backend/app/context/` | transitional home; Day 1 (v2) splits into `prompts/` + ChromaDB |
| `sandbox/start.py` | `start.py` (root) | launcher repointed to canonical paths |
| `sandbox/llama.cpp/`, model GGUF | referenced in place | not copied; located by the launcher as today |

~~**Gate D0**: from the repo root, `python start.py` brings up llama.cpp + the canonical FastAPI backend + the canonical Vite frontend, and a query the sandbox answers returns the same response — now served entirely from the canonical paths. `sandbox/` still runs independently via `python sandbox/start.py`. This parity check is the green light into Day 1.~~ *(See completion note above — Gate D0 passed 2026-06-26.)*

---

### Day 1 — The Agentic Core (DB-less) ✅ COMPLETE — 2026-07-02

*Goal: the full seven-agent pipeline running end-to-end with real verification, persistent memory, and auto-exploration — fed entirely by the `soundwave/` files, no database server anywhere.*

- [x] Typed envelope: `DBProfile`, `Intent`, `SqlCandidate`, `VerifyReport`, `AgentEvent`, `QueryResult` (Pydantic) — carried verbatim from `legacydocs/DAY1_PLAN_v1.md` Step 3.
- [x] `DBConnector` protocol + **`SoundwaveFileConnector`** *(generalized/renamed `FileConnector(db_name)` on 2026-07-03 — see the Multi-Database Restructure note in the header)*: transpile `01_…schema.sql` + `02_…data.sql` MySQL→SQLite with sqlglot, load into in-memory SQLite; introspection reads the parsed schema AST; `execute_read` returns real rows from seed data with forced `LIMIT`.
- [x] `LLMService` with **instruction hot-swap**: llama.cpp client + `load_adapter(name)` that activates `backend/app/prompts/<name>.md` as the system-prompt head (GGUF branch stubbed, wired Day 4+).
- [x] **Context Manager + file auto-exploration** (named priority): schema graph from the parsed SQL; glossary/coded-values/source-of-truth from `02_soundwave_context.md`; edge-case taxonomy from `03_soundwave_edge_cases.md`; all embedded into ChromaDB.
- [x] **Query Understanding, Clarification, SQL Generator, Verification** agents — full 3-layer chain (sqlglot AST + SQLite `EXPLAIN` + schema-linking + sanity heuristics).
- [x] **Session Manager**: SQLite persistence, multi-turn memory threaded through the orchestrator.
- [x] Orchestrator with dynamic routing (clarification branch, 1 repair loop); routes `/query`, `/session`, `/health`, `/db`; WebSocket `/ws`.

**Gate D1**: ✅ PASSED — 2026-07-02 — `python tests/gate_d1.py` scored **6/8** on the edge-case probes (EC-01…EC-08) against the file connector, meeting the ≥ 6/8 bar. EC-07/EC-08 were correctly stopped at the syntax-verification layer (the base 3B model emitted SQL the engine's `EXPLAIN` rejected — the fail-safe chain refusing to execute unverified SQL, exactly as designed). Adapter events fired for every LLM agent, and sessions persist across a backend restart. No MySQL process exists on the machine.

> **Sandbox detachment (2026-07-02):** with Day 1 green, the frozen `sandbox/` was **deleted**. The GGUF model moved to `models/` (repo root, gitignored), `llama-server` resolves from winget/PATH, the live chat frontend was repointed to the agentic `/query` stream, and the `/chat` + `/benchmark` prompt context now comes from the `databases/soundwave/` source files (moved there 2026-07-03, see the Multi-Database Restructure note above). See the Day 0 post-migration note above.

### Day 2 — Frontend Rebuild (No Tailwind) & Visualization ✅ COMPLETE — 2026-07-02

*Goal: the didactic UI — a learner sees the reasoning, the schema, the chart, and the lesson.*

> **As-built amendments (2026-07-02, full realignment record in `DAY2_PLAN.md`):** the sandbox
> detachment had already left a working chat MVP in `frontend/src/`, so Day 2 was executed as an
> evolve-in-place refactor, not a from-scratch build. Deltas vs the original step list:
> **(0)** transport stayed **NDJSON streaming over `POST /query`** — `/ws` remains live on the
> backend but unwired (cut-line #4 in §10 satisfied trivially); **(1)** `AgentProgress` gained the
> **adapter badge** (`profile: <name>` / `base` from `payload.adapter`) — the same signal Day 3's
> A/B harness reuses; **(2)** `DBProfileForm` ships **read-only** (the "map of the database" card);
> the editable characterization survey defers to Day 4 when an unknown DB can first appear;
> **(3)** `QueryBuilder` was **cut as a separate input mode** in favor of **inline autocomplete**
> in the existing free-text box (curated synonyms + schema vocabulary mined from `GET /db/profile`);
> **(4)** no formal component kit (Button/Card/Dialog/Tabs) — new components carry their own
> `*.module.css` on the shared tokens instead; `index.css` migrates incrementally.

- [x] Styling foundation: `styles/tokens.css` (shared scales + the 5 glass-theme palettes + CVD-validated `--chart-1/2/3` series colors) + per-component CSS Modules. No Tailwind, no shadcn.
- [x] Zustand stores (query, session, db-profile, progress).
- [x] Components: inline autocomplete in `InputArea` *(replaces `QueryBuilder`, amendment 3)*, `AgentProgress` with adapter badges *(NDJSON, amendments 0–1)*, `Visualization` (Recharts, heuristic-selected: stat tiles / line / bar / scatter, table always as complement), `SessionLibrary` (drawer), `DBProfileForm` (read-only drawer card, amendment 2).
- [x] **Didactic layer**: each answer renders four panels — *What I understood*, *The SQL (highlighted)*, *Why this query* (rationale + 3-layer verification checklist), *Results + chart*. Reuses `sqlHighlighter.ts` and `markdownRenderer.ts`.
- [x] End-to-end wire: NL → understanding → SQL → verify → execute (file connector) → results → auto-chart.

**Gate D2**: ✅ PASSED — 2026-07-02 — a non-SQL user runs a query end-to-end in the browser, sees live per-agent progress with adapter badges, a rendered chart, and the plain-language "why" as distinct panels. Bundle scan: zero Tailwind artifacts.

> **Known issue pending (KI-1, tracked in `DAY2_PLAN.md` §Known Issues):** restoring a session from
> `SessionLibrary` loads only the user questions — the assistant answers don't render. The restore
> path (assistant-turn persistence over `GET /session/{id}` and/or the frontend reconstruction in
> `queryStore.loadFromSession`) must be improved.

### Day 3 — Instruction Registry, Hot-Swap Discipline & Evaluation ✅ COMPLETE — 2026-07-03

*Goal: the "LoRA layer" without the training — a per-agent adapter registry that swaps instruction profiles today and GGUF adapters tomorrow, plus the measurement harness that will later prove the adapters' worth.*

> **As-built amendment (2026-07-03, full record in `DAY3_PLAN.md`):** the registry's `activate(agent)` call is made by the **orchestrator**, once per agent, immediately before that agent runs — not by each agent module self-activating as Day 1 had it. This lets the label ride on that agent's own `"started"` `AgentEvent` payload (the badge Day 2 already renders from `payload.adapter`, regardless of event status) instead of a separate `"progress"` event racing it. `chat_with_meta()` was added to `llm_service.py` (additive; `chat()` is byte-identical) and wired through `sql_generator.py` only, so the evaluation harness — a black-box HTTP client, same as `gate_d1.py` — can observe tokens/sec via the `sql_generator` `"done"` payload.

- [x] **Adapter registry**: `adapters/registry.json` mapping agent → `{kind, artifact}` (`"prompt"` now, `"gguf"` falls through to the same-named prompt until trained adapters land); `backend/app/services/adapter_registry.py` wraps `llm_service.load_adapter/unload_adapter/active_adapter`; orchestrator calls `adapter_registry.activate(agent)` before each of the 4 LLM-agent turns.
- [x] Authored the four **instruction profiles** as first-class prompt artifacts: `sql_generator.md`, `query_understanding.md`, `verification.md`, `clarification.md` — each tuned against EC-01…EC-08 from the soundwave edge-case taxonomy.
- [x] **A/B harness** (`tests/ab_harness.py`): toggles `registry.json` empty vs. as-authored, runs the EC suite both ways, writes `data/benchmarks/ab_report_<date>.json` with the pass-count/latency delta. Requires a live backend to execute (same precondition as `gate_d1.py`) — the file itself is written, lint-clean, and ready to run.
- [x] Evaluation harness (`tests/evaluate.py`): execution accuracy (hand-derived from `02_soundwave_data.sql` for EC-01–EC-06 and EC-08; EC-07 is date-relative against a frozen dataset and intentionally `not_scored`), per-stage latency from `AgentEvent` timestamps, tokens/sec via the `chat_with_meta` wiring above — persisted as `data/benchmarks/eval_<date>.json` + a markdown table.
- [x] Tests: 24-test `pytest` suite (`tests/conftest.py` + `test_adapter_registry.py`, `test_file_connector.py`, `test_verification.py`, `test_orchestrator.py`) covering the registry, `FileConnector`, the verification 3-layer chain, and orchestrator routing (clarification branch, repair loop) — all offline, no live llama.cpp needed. `pyproject.toml` configures `ruff`/`black`; `eslint.config.js` + `.prettierrc.json` added for the frontend.

**Gate D3**: ✅ registry swap observable per agent in the `AgentEvent` stream (label on the `"started"` event); `pytest tests/` green (24/24); a missing/deleted profile falls back to `base` without breaking the pipeline (already guaranteed by `llm_service.load_adapter`'s existing fail-safe, now reached through the registry — covered by `test_adapter_registry.py`). **A/B and evaluation reports themselves are not yet generated** — both harnesses need a running backend + llama.cpp server and are left for a manual run (see `DAY3_PLAN.md`'s Gate D3 checklist for the exact commands).

> **Data quirk found while deriving `evaluate.py`'s ground truth:** `gate_d1.py`'s EC-08 probe asks for playlists containing tracks "by Adele" — no such artist exists among soundwave_db's 12 artists, so the correct answer is 0 rows, meaning EC-08 can never pass the `row_count > 0` heuristic `gate_d1.py`/`ab_harness.py` use, even with perfect SQL. `evaluate.py`'s accuracy checker scores EC-08 correctly (expects 0); `gate_d1.py` itself was left untouched per Day 3's "import, don't duplicate" instruction.

### Day 4 — Real DB Connection & Hardening

*Goal: the physical database arrives last and nothing above it notices.*

- [ ] Stand up MySQL locally; load `databases/soundwave/01_…sql`, `02_…sql`, `03_…sql`; confirm 19 tables and seed counts (v1 Day 1 Step 4).
- [ ] Implement `MySQLConnector` (v1 Day 1 Step 5 code) behind the existing `DBConnector` protocol; introspection now reads `information_schema`. Match `FileConnector`'s constructor shape — `MySQLConnector(db_name: str)` — so `get_connector(db_name)` (generalized 2026-07-03) can hand it whichever database was selected without a special case.
- [ ] Connector switch via config: `IDI_CONNECTOR=file|mysql` — one flag, no agent code touched.
- [ ] **Parity check**: re-run the full EC suite on MySQL; results must match the file connector run.
- [ ] `docker-compose` (backend + llama.cpp + MySQL) and an updated `RUN_GUIDE`.
- [ ] **Skeptical review pass**: re-run all gates on both connectors; confirm the file connector remains the zero-setup demo path.

**Gate D4**: EC suite green on MySQL with identical results to the file connector; `IDI_CONNECTOR=file` still boots with zero DB setup; one-command bring-up works; verification never lets malformed SQL execute.

### Post-sprint — LoRA Training (deferred, seam already built)

Colab + Unsloth per §8. Each trained adapter lands as `adapters/<agent>.gguf`; flipping the registry entry from `prompt:` to `gguf:` activates it. The Day 3 A/B report is the baseline it must beat.

### Pending backlog (tracked, not yet scheduled — added 2026-07-14)

- [ ] **Sanity-layer rejection thresholds**: formalize the result-plausibility rejection thresholds of the verification chain's sanity layer, and calibrate them during the formal evaluation (OE4). Currently the layer enforces read-only + DDL/DML blocking; plausibility checks have no formal thresholds.
- [ ] **Didactic wait phrases**: show rotating phrases/facts about databases in the frontend while the pipeline is answering. UX decision: we do not estimate remaining time — a slow answer is acceptable if the wait itself teaches.

---

## 6. DB Auto-Exploration & Characterization Forms

This is the heart of the didactic reframe and one of your named priorities. When IDI connects to *any* source — a live MySQL server (Day 4+) or, during the sprint, one of the file-based `databases/<db_name>/` folders (currently just `soundwave`, discovered dynamically) — it does two things in concert:

1. **Automatic introspection** (machine): Days 1–3, parse `01_soundwave_schema.sql` with sqlglot → tables, columns, types, PKs, FKs, nullability; Day 4+, read `information_schema` for the same facts. Either way: infer the relationship graph; detect coded columns (low-cardinality integers/enums), nullable FKs, self-references, and pre-aggregated/cached columns — exactly the soundwave taxonomy, generalized.
2. **Guided characterization survey** (human): a short, progressive form where the connector/learner confirms or enriches what introspection guessed. The form *teaches while it asks*.

| Survey section | What it asks | Feeds |
|---|---|---|
| Domain | One-line description of the business this DB models | Context embeddings, glossary |
| Glossary | Plain-language meaning of abbreviated columns (`trk_dur_ms`, `is_exp`, `usr_acq_src`) | Schema linking (EC-05) |
| Coded values | Meaning of integer/enum codes (`plan_type 1–4`, `status 0/1/2`) | Value mapping (EC-02) |
| Source of truth | Which column is canonical when raw vs cached disagree | Sanity layer (EC-07) |
| Sensitivity | Read-only? columns to never surface? | Safety guard |

The output is a persisted **`DBProfile`** — a "profile card" the learner can read like a map of the database. It is the shared context every downstream agent consumes, and it makes IDI portable to databases it has never seen.

---

## 7. Memory & Persistence Design

| Concern | Store | Notes |
|---|---|---|
| Sessions (turns, SQL, results, charts) | **SQLite** | local-first; JSON columns for flexible payloads; save/load/search |
| Multi-turn conversational memory | SQLite + orchestrator state | last-N turns + resolved entities threaded into Query Understanding |
| Domain/schema context | **ChromaDB** | embeddings of schema graph + `DBProfile` + context md for semantic retrieval |
| Adapters | `adapters/registry.json` + `prompts/*.md` now; `adapters/*.gguf` post-sprint | hot-swapped by `LLMService` through one `load_adapter()` seam |

Memory persistence is treated as a first-class Day-1 deliverable, not an afterthought, because continuity is what turns a single answer into a learning session.

---

## 8. Adapter Layer — Instruction Profiles Now, LoRA Training Post-Sprint

**v2 reframe.** The sprint ships the *hot-swap discipline*, not the training. Each agent's specialization lives in an **instruction profile** (`backend/app/prompts/<agent>.md`) activated through the same `load_adapter(name)` call that will later load GGUF adapters. The registry (`adapters/registry.json`) records which artifact each agent runs on:

| Agent | Sprint artifact (Day 3) | Post-sprint artifact | Dataset (when trained) |
|---|---|---|---|
| `sql_generator` | `prompt:sql_generator.md` | `gguf:sql_generator.gguf` | `gretelai/synthetic_text_to_sql` + soundwave samples |
| `query_understanding` | `prompt:query_understanding.md` | `gguf:query_understanding.gguf` | synthesized intent/entity set |
| `verification` | `prompt:verification.md` | `gguf:verification.gguf` | self-generated error/repair corpus |
| `clarification` | `prompt:clarification.md` | optional | custom dialogue set |

Training (deferred): Colab + Unsloth (T4/L4), ≤ 8 h per adapter; `r=16, alpha=32, dropout=0.05`, attention+MLP target modules, 3 epochs, lr `2e-4`, QLoRA 4-bit; export GGUF Q4_K_M.

> Risk cover unchanged: every agent runs on the **base model + base instructions** if its profile (or later, adapter) is missing — a swap failure never blocks the pipeline, it only lowers accuracy. The Day 3 A/B report is the baseline any trained adapter must beat to earn its registry slot.

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 7 agents too ambitious for 4 days | High | High | Sandbox loop is the always-working fallback; cut-lines in §10; agents ship incrementally behind the orchestrator |
| Colab session/quota limits | Medium | Low | ≤ 8 h budget; split across sessions; base-model fallback decouples training from delivery |
| llama.cpp LoRA hot-swap friction | Low | Low *(deferred)* | Instruction-profile swap carries the sprint; GGUF path lands post-sprint with `--lora` fallback |
| MySQL setup friction on Windows | Medium | Low *(moved to Day 4)* | File connector is the working default; Dockerized MySQL in compose as backup |
| MySQL→SQLite transpile gaps in soundwave DDL/DML | Medium | Medium | sqlglot handles most dialect drift; patch remaining statements by hand once (files are frozen); parity check on Day 4 catches divergence |
| Frontend rebuild eats the schedule | Medium | Medium | Token system first; reuse existing highlighter/renderer; keep component kit minimal |
| Verification false-negatives execute bad SQL | Low | High | Read-only connector + forced LIMIT make execution safe even if a layer misses |

---

## 10. Cut-Lines (If Behind Schedule)

Drop from the bottom up; each cut keeps a working, demoable system.

1. `clarification` instruction profile → use base model prompting.
2. ChromaDB semantic retrieval → fall back to direct `DBProfile` injection (static context, as the sandbox does today).
3. `verification` instruction profile → keep the rule-based 3-layer chain (it is already non-LLM and sufficient).
4. WebSocket per-agent progress → poll a status endpoint (as the sandbox benchmark already does).
5. Day 4 MySQL connection → ship on the file connector only; `MySQLConnector` stays as the documented, coded-but-unwired extension point.

**Never cut**: the three-layer verification chain, the read-only execution guard, and the didactic "why" panel — they are the thesis contribution and the new identity of the product.

---

## 11. Definition of Done

| Criterion | Target | Measurement |
|---|---|---|
| Pipeline completeness | All 7 modules invoked on a real query | Trace of `AgentEvent`s |
| SQL execution accuracy (soundwave) | ≥ 75% | Edge-case suite, execution match |
| Verification catch rate | ≥ 88% | Injected-error corpus |
| Never executes unverified SQL | 100% | Guard test, attempted bad SQL |
| Latency (simple / complex) | < 5 s / < 15 s | Benchmark timing |
| VRAM with active adapter | < 3.5 GB | Runtime monitor |
| No Tailwind in build | 0 references | Bundle/source scan |
| Reproducible bring-up | One command | `docker-compose up` |
| Didactic layer present | Every answer | "What/SQL/Why/Results" panels render |

---

## 12. References

- Base model — [Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF)
- Inference + LoRA — [llama.cpp](https://github.com/ggerganov/llama.cpp)
- Training — [Unsloth docs](https://docs.unsloth.ai/)
- Datasets — [gretelai/synthetic_text_to_sql](https://huggingface.co/datasets/gretelai/synthetic_text_to_sql), [b-mc2/sql-create-context](https://huggingface.co/datasets/b-mc2/sql-create-context), [Spider](https://yale-lily.github.io/spider)
- SQL parsing — [sqlglot](https://github.com/tobymao/sqlglot)
- Frontend — [Recharts](https://recharts.org/), [Zustand](https://github.com/pmndrs/zustand)
- Vector store — [ChromaDB](https://www.trychroma.com/)
- Internal — `databases/soundwave/00_soundwave_db_documentation.md`, `databases/soundwave/02_soundwave_context.md`, `databases/soundwave/03_soundwave_edge_cases.md`, `databases/soundwave/04_soundwave_survey.json`

---

*The sandbox proved the loop hums. These four days give it structure, memory, sight, and a voice that teaches — turning a clever proof-of-concept into a system that lets anyone read a database in their own words.*
