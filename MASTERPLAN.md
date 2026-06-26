# IDI — 4-Day Implementation Masterplan

**From single-prompt prototype to multi-agent didactic NL2SQL engine.**

Universidad Nacional de Colombia — Computer and Systems Engineering Thesis — 2026
Author: Juan David Ramírez Torres (`jdramirezt@unal.edu.co`)
Plan window: a **Day 0** prep step (repo skeleton + sandbox migration) followed by 4 working days. Companion to `sandbox/GAP_ANALYSIS.md` and `PROJECT_BRIEF.md`.

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
| D2 | LoRA training | **Google Colab + Unsloth (T4/L4), ≤ 8 h per adapter.** Not the local GTX 1650. | Training runs **off the local critical path**; local machine stays free for development. Adapters are pulled as GGUF and hot-swapped into llama.cpp. |
| D3 | DB connectivity | **MySQL now, behind a thin `DBConnector` interface.** | Concrete `MySQLConnector` against soundwave today; a clean seam to add SQLite/Postgres later without touching agent logic. |
| D4 | Agent depth | **Full seven agents from the brief.** | Maximum thesis fidelity. Mitigated by reusing the working sandbox loop as the SQL-generation fallback so nothing regresses while agents are built. |

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
   QueryBuilder  Visualization  ProgressIndicator  SessionLibrary  DBProfileForm
        │  REST + WebSocket (per-step progress)
        ▼
FastAPI Backend
   Orchestrator  ──drives──▶  [1 Context Mgr] [2 Query Understanding]
                              [3 SQL Generator] [4 Verification]
                              [5 Visualization] [6 Session Manager]
        │                              │
        ▼                              ▼
   LLM Service (adapter controller)   DBConnector (thin interface)
   • llama.cpp /lora-adapters         • MySQLConnector → soundwave_db
   • hot-swap < 100 ms                • introspection + read-only execution
   • base-model fallback
        │                              │
        ▼                              ▼
   llama.cpp (Qwen2.5-Coder-3B)   ChromaDB (context)   SQLite (sessions)
   + LoRA adapters (GGUF)
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
    components/ QueryBuilder/ Visualization/ ProgressIndicator/
                SessionLibrary/ DBProfileForm/
    styles/ tokens.css + *.module.css
    stores/                 # Zustand
    services/ api.ts ws.ts
adapters/                   # *.gguf pulled from Colab
training/                   # Colab notebooks + data prep + lora_config
data/ benchmarks/ synthetic/
soundwave/                  # schema + data + edge cases (already present)
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

Each day ends with a **verification gate** — a concrete, failable check. The plan front-loads structure (your explicit priority: *"empecemos por las tareas más fundamentales para darle estructura al proyecto"*), then agents, then frontend, then integration.

### Day 0 — Repo Skeleton & Sandbox Migration *(pre-sprint)*

*Goal: stand up the canonical layout and prove the sandbox loop runs unchanged from its new home — with `sandbox/` frozen as a known-good fallback.*

This is the structural foundation the sprint builds on (your explicit priority: *"empecemos por las tareas más fundamentales para darle estructura al proyecto"*). No new behavior is added: the proven sandbox chat loop is **copied** into the canonical paths and must answer a query identically from there. `sandbox/` is left untouched as the reference implementation and runtime fallback.

- [ ] Scaffold the full canonical tree from §3 (`backend/app/...`, `frontend/src/...`, `adapters/`, `training/`, `data/`, `tests/`, `deployment/`) with package markers (`__init__.py`) and short placeholder `README`s in otherwise-empty dirs.
- [ ] Copy the working sandbox into canonical paths per the migration map below — **copy, not move**; `sandbox/` stays frozen.
- [ ] Resolve the top-level conflicts: delete the stray Flask `backend/app.py` (superseded by the FastAPI loop) and clear the 0-byte stubs that collide with copied files; keep a stub only where it marks a genuine Day-1+ target.
- [ ] Port `sandbox/start.py` to a root-level `start.py` that launches llama.cpp + backend + frontend from the **canonical** paths (binary and model located as today; the heavy `llama.cpp/` build is referenced in place, not copied).
- [ ] Smoke-test the migrated tree end-to-end.

**Migration map:**

| Sandbox source (frozen) | Canonical destination | Note |
|---|---|---|
| `sandbox/backend/main.py` | `backend/app/main.py` | FastAPI entry; the proven chat loop becomes the SQL fallback Day 1 wraps |
| `sandbox/backend/requirements.txt` | `backend/requirements.txt` | dependency baseline |
| `sandbox/frontend/src/` (App, components, utils, `index.css`) | `frontend/src/` | `sqlHighlighter.ts` / `markdownRenderer.ts` carried forward verbatim |
| `sandbox/frontend/{index.html, package.json, vite.config.ts, tsconfig.json}` | `frontend/` | build config |
| `sandbox/context/` (`DB_context.md`, `SYSTEM_PROMPT.md`) | `backend/app/context/` | transitional home; Day 2 splits into `prompts/` + ChromaDB |
| `sandbox/start.py` | `start.py` (root) | launcher repointed to canonical paths |
| `sandbox/llama.cpp/`, model GGUF | referenced in place | not copied; located by the launcher as today |

**Gate D0**: from the repo root, `python start.py` brings up llama.cpp + the canonical FastAPI backend + the canonical Vite frontend, and a query the sandbox answers returns the same response — now served entirely from the canonical paths. `sandbox/` still runs independently via `python sandbox/start.py`. This parity check is the green light into Day 1.

---

### Day 1 — Foundations & Contracts

*Goal: a running skeleton that routes a request through a (stubbed) 7-agent pipeline and can talk to soundwave.*

- [ ] (Day 0 already delivered the canonical skeleton.) Wrap the migrated sandbox loop as the fallback SQL path inside `services/llm_service.py` — no regression against Gate D0.
- [ ] Stand up MySQL locally; load `soundwave/01_…sql`, `02_…sql`, `03_…sql`; confirm 19 tables and seed counts.
- [ ] Define the typed envelope: `DBProfile`, `Intent`, `SqlCandidate`, `VerifyReport`, `AgentEvent` (Pydantic).
- [ ] Implement `DBConnector` protocol + `MySQLConnector` (introspection + read-only execution with forced `LIMIT`).
- [ ] Implement `LLMService`: llama.cpp client, `/lora-adapters` hot-swap wrapper, base-model fallback.
- [ ] Orchestrator skeleton: deterministic pipeline emitting per-step `AgentEvent`s; FastAPI routes `/query`, `/session`, `/health`, `/db`; WebSocket `/ws`.
- [ ] **Colab: kick off `sql_generator` training** (the critical adapter) so the ≤ 8 h clock starts on Day 1.

**Gate D1**: `POST /query` with *"How many tracks are standalone singles?"* returns a piped response (understanding → generated SQL → executed against soundwave), and the correct answer uses `album_id IS NULL` (EC-03). Progress events visible on `/ws`.

### Day 2 — The Seven Agents, Memory & Auto-Exploration

*Goal: real agents, real verification, persistent memory, and database self-characterization.*

- [ ] **Context Manager + DB auto-exploration** (your named priority): schema introspection → schema graph; ingest `02_soundwave_context.md`; build the **characterization survey** (see §6); embed schema + context into ChromaDB.
- [ ] **Query Understanding**: intent/entity/metric/filter extraction + ambiguity detection (base model until LoRA lands).
- [ ] **Clarification**: generate follow-ups when ambiguity flags fire.
- [ ] **SQL Generator**: NL→SQL with rationale, grounded in `DBProfile`.
- [ ] **Verification Agent**: full 3-layer chain (`sqlglot` + `EXPLAIN` + schema-linking + sanity heuristics).
- [ ] **Session Manager**: SQLite persistence — save/load/search, multi-turn memory threaded through the orchestrator (your named priority: *persistencia de la memoria*).
- [ ] Orchestrator dynamic routing: clarification branch + retry-on-verify-fail (max 1 repair loop).

**Gate D2**: run 8 probe queries, one per soundwave edge-case code (EC-01…EC-08); ≥ 6/8 pass verification and return correct rows. Sessions survive a backend restart.

### Day 3 — Frontend Rebuild (No Tailwind) & Visualization

*Goal: the didactic UI — a learner sees the reasoning, the schema, the chart, and the lesson.*

- [ ] Styling foundation: `tokens.css` (port glass theme) + CSS Modules; small component kit (Button, Card, Dialog, Tabs). No Tailwind, no shadcn.
- [ ] Zustand stores (query, session, db-profile, progress).
- [ ] Components: `QueryBuilder` (keyword-guided), `ProgressIndicator` (WebSocket, per-agent steps), `Visualization` (Recharts, auto-selected), `SessionLibrary`, `DBProfileForm` (the characterization survey UI).
- [ ] **Didactic layer**: each answer renders four panels — *What I understood*, *The SQL (highlighted)*, *Why this query* (join path + edge case), *Results + chart*. Reuse the existing `sqlHighlighter.ts` and `markdownRenderer.ts`.
- [ ] End-to-end wire: NL → understanding → SQL → verify → execute → results → auto-chart.

**Gate D3**: a non-SQL user runs a query end-to-end in the browser, sees live per-agent progress, a rendered chart, and the plain-language "why". Lighthouse/manual check confirms no Tailwind artifacts in the bundle.

### Day 4 — LoRA Hot-Swap, Evaluation & Hardening

*Goal: adapters live, accuracy measured, the build reproducible.*

- [ ] Pull trained adapters (GGUF) from Colab into `adapters/`; wire hot-swap per agent; **A/B base vs LoRA**.
- [ ] Evaluation harness: extend the sandbox benchmark to **execution accuracy** (now that we can execute) over the soundwave edge-case suite; record latency and tokens/sec.
- [ ] Tests: `pytest` for connector/verification/orchestrator; frontend smoke tests; configure `ruff`, `black`, ESLint, Prettier.
- [ ] `docker-compose` (backend + llama.cpp + MySQL) and an updated `RUN_GUIDE`.
- [ ] **Skeptical review pass**: re-run all four gates; confirm fallback path still works if an adapter is missing.

**Gate D4**: full pipeline green on soundwave benchmark with adapters loaded; one-command bring-up works; verification never lets malformed SQL execute.

---

## 6. DB Auto-Exploration & Characterization Forms

This is the heart of the didactic reframe and one of your named priorities. When IDI connects to *any* MySQL database, it does two things in concert:

1. **Automatic introspection** (machine): read `information_schema` → tables, columns, types, PKs, FKs, nullability, indexes; infer the relationship graph; detect coded columns (low-cardinality integers/enums), nullable FKs, self-references, and pre-aggregated/cached columns — exactly the soundwave taxonomy, generalized.
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
| Adapters | filesystem `adapters/*.gguf` | hot-swapped by `LLMService` |

Memory persistence is treated as a first-class Day-2 deliverable, not an afterthought, because continuity is what turns a single answer into a learning session.

---

## 8. LoRA Training Schedule (Colab, ≤ 8 h Each)

Training is off the local critical path (D2). One unattended Colab job per day; adapters land just in time for Day 4 integration. Config per brief: `r=16, alpha=32, dropout=0.05`, attention+MLP target modules, 3 epochs, lr `2e-4`, QLoRA 4-bit; export GGUF Q4_K_M.

| Day | Adapter | Dataset | Priority | Status target |
|---|---|---|---|---|
| Day 1 (kick off ~9:00 AM) | `sql_generator` | `gretelai/synthetic_text_to_sql` (+ soundwave-style samples) | Critical | trained by Day 2 AM |
| Day 2 | `query_understanding` | synthesized intent/entity set | High | trained by Day 3 AM |
| Day 3 | `verification` | self-generated error/repair corpus | Medium | trained by Day 4 AM |
| Day 4 (if time) | `clarification` | custom dialogue set | Optional | nice-to-have |

> Risk cover: every agent runs on the **base model** until its adapter arrives, so a late or weak adapter never blocks the pipeline — it only lifts accuracy.

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 7 agents too ambitious for 4 days | High | High | Sandbox loop is the always-working fallback; cut-lines in §10; agents ship incrementally behind the orchestrator |
| Colab session/quota limits | Medium | Low | ≤ 8 h budget; split across sessions; base-model fallback decouples training from delivery |
| llama.cpp LoRA hot-swap friction | Low | Medium | Fallback to single `--lora` at launch, or Ollama Modelfiles |
| MySQL setup friction on Windows | Medium | Medium | Document exact steps in RUN_GUIDE; Dockerized MySQL in compose as backup |
| Frontend rebuild eats the schedule | Medium | Medium | Token system first; reuse existing highlighter/renderer; keep component kit minimal |
| Verification false-negatives execute bad SQL | Low | High | Read-only connector + forced LIMIT make execution safe even if a layer misses |

---

## 10. Cut-Lines (If Behind Schedule)

Drop from the bottom up; each cut keeps a working, demoable system.

1. `clarification.gguf` adapter → use base model prompting.
2. ChromaDB semantic retrieval → fall back to direct `DBProfile` injection (static context, as the sandbox does today).
3. `verification.gguf` adapter → keep the rule-based 3-layer chain (it is already non-LLM and sufficient).
4. WebSocket per-agent progress → poll a status endpoint (as the sandbox benchmark already does).
5. Multi-engine seam exercised → ship MySQL-only; the `DBConnector` interface stays as the documented extension point.

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
- Internal — `PROJECT_BRIEF.md`, `sandbox/GAP_ANALYSIS.md`, `soundwave/02_soundwave_context.md`, `soundwave/03_soundwave_edge_cases.md`

---

*The sandbox proved the loop hums. These four days give it structure, memory, sight, and a voice that teaches — turning a clever proof-of-concept into a system that lets anyone read a database in their own words.*
