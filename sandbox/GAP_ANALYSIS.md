# Sandbox vs. Project Brief — Gap Analysis

## What IS Implemented

| Area | Status | Details |
|------|--------|---------|
| **LLM Infrastructure** | Done | llama.cpp + Qwen2.5-Coder-3B-Instruct (Q4_K_M), running locally on port 7860 with GPU offload (`-ngl 99`) |
| **FastAPI Backend** | Partial | Single `/chat` endpoint proxying to llama.cpp. No routing, no agent separation — just a thin HTTP relay (`backend/main.py`) |
| **React Frontend** | Partial | Chat UI with 6 components: Header, ChatBox, MessageBubble, TypewriterMessage, GeneratingIndicator, InputArea |
| **System Prompt Engineering** | Done | Comprehensive NL2SQL prompt in `context/SYSTEM_PROMPT.md` with 6-phase reasoning loop, safety layers, and output format rules |
| **Context Auto-Loading** | Done | All files in `context/` are read into the system prompt per request |
| **SQL Syntax Highlighting** | Done | Full tokenizer in `frontend/src/utils/sqlHighlighter.ts` |
| **Markdown Rendering** | Done | Section filtering (Business Interpretation / SQL / Interpretation), think-tag stripping (`frontend/src/utils/markdownRenderer.ts`) |
| **Theming** | Done | 5 glass-morphism themes, persisted to localStorage |
| **Typewriter Animation** | Done | Character-by-character output with skip-on-click |
| **Metrics Display** | Done | Token counts, generation time, tokens/sec shown per message |
| **Launcher** | Done | `start.py` — manages all 3 servers with health checks and nvm-windows registry workaround |

---

## What is NOT Implemented (Gaps vs. Project Brief)

### 1. Multi-Agent Architecture (the core differentiator)

The brief specifies **7 specialized modules** — the sandbox has **zero agents**. Everything goes through a single monolithic prompt.

| Agent | Brief Spec | Sandbox Status |
|-------|-----------|----------------|
| **Context Manager** | Domain knowledge via surveys + ChromaDB embeddings | Missing — context is static text files, no embeddings, no surveys |
| **Query Understanding** | Intent parsing, ambiguity detection, entity extraction | Missing — raw user text goes straight to LLM |
| **SQL Generator** | Dedicated NL2SQL with LoRA adapter | Missing — base model handles everything, no LoRA adapter |
| **Verification Agent** | 3-layer checking (syntax → semantic → sanity) | Missing — no verification at all, LLM output shown as-is |
| **Visualization Engine** | Automatic chart selection + Recharts rendering | Missing — text-only output, no charts |
| **Session Manager** | Persistent sessions, save/load/search | Missing — chat resets on page refresh |
| **Orchestrator** | Dynamic workflow routing between agents | Missing — no routing logic exists |

### 2. LoRA Fine-Tuning

- **Brief**: 4 task-specific LoRA adapters (sql_generator, query_understanding, verification, clarification) with hot-swap via `/lora-adapters` API
- **Sandbox**: Uses the raw base model only. No adapters trained, no hot-swap logic, no `/lora-adapters` calls

### 3. Frontend Stack Gaps

| Feature | Brief Spec | Sandbox Status |
|---------|-----------|----------------|
| **Zustand** state management | Specified | Not used — plain `useState` in App.tsx |
| **shadcn/ui** components | Specified | Not used — custom CSS only |
| **Tailwind CSS** | Specified | Not used — raw CSS in index.css |
| **Recharts** visualization | Specified | Not installed, no charts |
| **WebSocket** real-time updates | Specified | Not used — standard HTTP fetch |
| **Query Builder** (keyword-guided) | Specified | Not built — plain text input only |
| **Session Library** UI | Specified | Not built |
| **Progress Indicator** (multi-step) | Specified | Basic "Thinking..." dots only, no per-agent progress |

### 4. Backend Architecture Gaps

| Feature | Brief Spec | Sandbox Status |
|---------|-----------|----------------|
| **Structured API routes** (query, session, health) | Specified | Single `/chat` endpoint |
| **LLM Service** (adapter management) | Specified | Direct HTTP call to llama.cpp |
| **Orchestrator service** | Specified | Not built |
| **SQL Executor** (database execution) | Specified | Not built — SQL is displayed but never executed |
| **ChromaDB** vector store | Specified | Not installed |
| **SQLite/PostgreSQL** session storage | Specified | Not installed |
| **WebSocket endpoint** | Specified | Not built |
| **Prompt templates per agent** | Specified | Single monolithic system prompt |

### 5. Infrastructure Gaps

| Feature | Brief Spec | Sandbox Status |
|---------|-----------|----------------|
| **Docker / Docker Compose** | Specified | Not set up |
| **pytest tests** | Specified | No tests written |
| **Jest tests** | Specified | No tests written |
| **ESLint / Prettier** | Specified | Not configured |
| **ruff / black** | Specified | Not configured |

### 6. Evaluation Infrastructure

- No Spider/BIRD benchmark integration
- No user study framework (SUS questionnaire)
- No accuracy measurement pipeline

---

## Summary

The sandbox is a **functional single-agent chat prototype** — it proves the core loop works (user types NL → LLM generates SQL → formatted output). It covers roughly **15-20% of the full brief**. The major remaining work falls into three buckets:

1. **Agent decomposition** — splitting the monolithic prompt into 7 specialized agents with an orchestrator and LoRA hot-swap (this is the thesis contribution)
2. **Frontend upgrade** — migrating to Tailwind/shadcn/Zustand, adding visualization (Recharts), WebSocket progress, session library, and query builder
3. **Infrastructure** — ChromaDB, session persistence, Docker, testing, benchmarking pipeline

The sandbox is a solid proof-of-concept foundation, but the multi-agent architecture, LoRA adapters, and verification chain — which are the core academic contributions — are entirely ahead.
