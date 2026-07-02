# IDI (Intelligent Database Interface) Development Guide

Multi-agent NL2SQL system — a **didactic instrument** that lets anyone query, learn, and understand a real database in plain language.

## Current Status

**Phase 0 (Repo Skeleton & Sandbox Migration): ✅ COMPLETE — 2026-06-26**
**Day 1 (The Agentic Core, DB-less): ✅ COMPLETE — 2026-07-02** — Gate D1 PASSED (6/8 EC probes; EC-07/EC-08 correctly blocked by the syntax-verification layer — fail-safe working as designed). The full seven-agent pipeline runs end-to-end over `/query`, fed entirely by the `soundwave/` files via `SoundwaveFileConnector`.
**Sandbox Detachment: ✅ COMPLETE — 2026-07-02** — the frozen `sandbox/` has been **deleted**. The GGUF model now lives at `models/` (repo root, gitignored) and `llama-server` resolves from winget/PATH. The live frontend chat calls the agentic `/query` pipeline (soundwave-grounded); the legacy `/chat` + `/benchmark` loops build their prompt from the soundwave source files. Nothing in the tree references `sandbox/` anymore.
**REPLAN v2 — 2026-07-02**: sprint order inverted — agents first, physical DB last. Days 1–3 run DB-less on a `SoundwaveFileConnector` (in-memory SQLite built from `soundwave/*.sql`); LoRA *training* is deferred and the hot-swap seam swaps **instruction profiles** (`backend/app/prompts/<agent>.md`) via the same `load_adapter()` API that will later load GGUF adapters.
Active phase: **Day 2 — Frontend** (`DAY2_PLAN.md`) — note the chat UI is already repointed to `/query` with a live agent-progress stream + results table as part of the sandbox detachment.
New order: D1 agents → D2 frontend → D3 instruction registry + evaluation → D4 real MySQL connection.
See `MASTERPLAN.md` for the full plan; v1 day plans are archived in `legacydocs/DAY*_PLAN_v1.md` and remain the code reference for carried-over steps.

## Active Documentation

| Doc | Purpose |
|---|---|
| `MASTERPLAN.md` | Single source of truth: architecture, agent contracts, day-by-day plan |
| `CLAUDE.md` | This file — dev guidelines & assistant orientation |
| `docs/TECHNOLOGY_DEEP_DIVE.md` | Deep dives on ChromaDB, SQLite, Recharts, LoRA, WebSockets, GGUF |
| `soundwave/02_soundwave_context.md` | DB domain context (schema narrative, business rules) |
| `soundwave/03_soundwave_edge_cases.md` | EC-01…EC-08 edge-case taxonomy — the verification test syllabus |

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
