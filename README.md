# IDI (Intelligent Database Interface)

## Overview

IDI is a modular, multi-agent Natural Language to SQL (NL2SQL) system designed to enable non-technical executives and managers to extract statistical insights from relational databases through natural language queries, without requiring SQL expertise or technical intermediaries.

**Academic Context**: Computer and Systems Engineering Thesis, Universidad Nacional de Colombia

**Author**: Juan David Ramírez Torres (<jdramirezt@unal.edu.co>)
**Semester**: 2026-1S (February 2 – May 30, 2026)

---

## Current Implementation Status

> **Milestones:** Phase 0 (Repo Skeleton & Sandbox Migration) ✅ 2026-06-26 · Day 1 (Agentic Core, DB-less) ✅ 2026-07-02 — Gate D1 **PASSED (6/8)** · Sandbox fully detached ✅ 2026-07-02.

What actually runs today via `python start.py`:

- **Seven-agent pipeline over `POST /query`** — Context Manager → Query Understanding → (Clarification) → SQL Generator → Verification → Orchestrator, streamed to the UI as NDJSON: a sequence of agent-progress events followed by a final result carrying the generated SQL, the 3-layer verification report, the executed rows, and a plain-language teaching summary. A WebSocket `/ws` mirror is also available.
- **DB-less data source (REPLAN v2)** — Days 1–3 run with **no database server**. `SoundwaveFileConnector` builds an in-memory SQLite from the `soundwave/` fixture files (`01_…schema.sql` + `02_…data.sql`, transpiled MySQL→SQLite with sqlglot); the domain context (`02_soundwave_context.md`, `03_soundwave_edge_cases.md`) is embedded into ChromaDB. A real MySQL connection arrives on Day 4.
- **Instruction-profile hot-swap (LoRA seam, not GGUF yet)** — `load_adapter()` swaps per-agent system prompts from `backend/app/prompts/<agent>.md`. This is the same API that will later load GGUF LoRA adapters; adapter *training* is deferred.
- **Local inference, fully detached** — `llama-server` (from winget/PATH) hosts Qwen2.5-Coder-3B-Instruct (Q4_K_M) loaded from `models/`; no cloud calls. The old `sandbox/` prototype that vendored llama.cpp + the model has been **removed** — nothing references it anymore.
- **Chat + Benchmarks UI** — React + TypeScript with **CSS Modules + design tokens** (no Tailwind, no shadcn/ui). The chat shows the live agent-progress stream, syntax-highlighted SQL, and a results table; the Benchmarks page compares CPU vs GPU on soundwave edge-case queries. Recharts visualization lands in Day 2.

The sections below describe the **target** thesis architecture; where the current build differs, it is noted inline.

---

## The Problem

Modern executives possess strategic vision but lack SQL knowledge to validate intuitions with data. Current barriers include:

- **85% of organizational decision-makers lack SQL proficiency**, creating dependency bottlenecks on data analysts
- **Decision latency**: Strategic decisions delayed hours or days awaiting technical query execution
- **Resource misallocation**: Skilled data professionals occupied with routine reporting tasks
- **Communication friction**: Semantic gaps between business questions and technical implementations

---

## The Solution

IDI transforms ambiguous natural language questions into verified statistical insights through:

1. **Context Acquisition**: Structured surveys capture enterprise-specific domain knowledge, business logic, and terminology
2. **Ambiguity Resolution**: Keyword-guided interfaces combined with clarification dialogues resolve underspecification
3. **Multi-Agent Architecture**: Seven specialized modules orchestrate interpretation, SQL generation, and error correction
4. **Three-Layer Verification**: Syntax, semantic, and sanity checking ensures >90% query correctness
5. **Automatic Visualization**: Intelligent chart selection and rendering for trend identification and analysis
6. **Local Deployment**: Optimized for consumer hardware (16GB RAM, 4GB VRAM) to minimize cloud dependency and costs

---

## System Architecture

### Seven Core Modules

1. **Context Manager Agent**: Acquires and maintains enterprise-specific domain knowledge through surveys and embeddings
2. **Query Understanding Agent**: Parses natural language, detects ambiguities, and generates clarification questions
3. **SQL Generator Agent**: Translates structured intent into executable SQL using fine-tuned LoRA adapters
4. **Verification Agent**: Validates correctness through three-layer checking (syntax → semantic → sanity)
5. **Visualization Engine**: Automatically selects and renders appropriate charts based on result structure
6. **Session Manager Agent**: Saves and manages query contexts for investigation continuity
7. **Multi-Agent Orchestrator**: Coordinates dynamic workflow routing and manages conversation state

### Key Design Principles

- **Modular Architecture**: Separation of concerns enables independent component evolution
- **Fail-Safe Design**: Verification layer prevents execution of malformed queries
- **Stateful Context**: Session management enables multi-turn conversational queries
- **Local-First**: Eliminates per-query API fees and keeps sensitive data on-premises
- **LoRA Hot-Swap**: Task-specific adapters switch in <100ms without model reloading

---

## Technology Stack

### Core LLM Infrastructure

| Component              | Technology                 | Specification                                     |
| ---------------------- | -------------------------- | ------------------------------------------------- |
| **Base Model**         | Qwen2.5-Coder-3B-Instruct  | Best SQL performance at 3B scale                  |
| **Quantization**       | Q4_K_M (GGUF format)       | ~2GB VRAM, 25-35 tokens/sec on GTX 1650           |
| **Inference Engine**   | llama.cpp                  | Native LoRA hot-swap via `/lora-adapters` API     |
| **Fine-tuning Method** | LoRA (Low-Rank Adaptation) | Task-specific adapters (~20-50MB each)            |
| **Training Platform**  | Google Colab + Unsloth     | Free T4 GPU, QLoRA support, 2-4 hours per adapter |

Model URL: https://huggingface.co/Triangle104/Qwen2.5-Coder-3B-Instruct-Q4_K_M-GGUF

### LoRA Adapters (Task-Specific Fine-Tuning)

> **Status:** *planned.* Today the hot-swap seam loads **instruction profiles** (`backend/app/prompts/<agent>.md`) through the same `load_adapter()` API; the GGUF adapters below are the Day 4+ target once training runs.

| Adapter                      | Purpose                                  | Training Dataset                                  | Priority |
| ---------------------------- | ---------------------------------------- | ------------------------------------------------- | -------- |
| **query_understanding.gguf** | Intent classification, entity extraction | Synthesized from SQL datasets                     | High     |
| **clarification.gguf**       | Generate follow-up questions             | Custom dialogue dataset                           | Optional |
| **sql_generator.gguf**       | NL → SQL translation                     | `gretelai/synthetic_text_to_sql` (15-20K samples) | Critical |
| **verification.gguf**        | SQL error detection and correction       | Self-generated error corpus                       | Medium   |

### Backend Stack

| Component           | Technology                       | Purpose                                                      |
| ------------------- | -------------------------------- | ------------------------------------------------------------ |
| **API Framework**   | FastAPI                          | Async support, auto-generated OpenAPI docs, WebSocket native |
| **LLM Service**     | llama.cpp server                 | Model hosting with LoRA adapter management                   |
| **Vector Database** | ChromaDB                         | Context embeddings storage and semantic search               |
| **Session Storage** | SQLite (dev) / PostgreSQL (prod) | Session persistence with JSONB for flexible data             |
| **Cache Layer**     | In-memory / Redis (optional)     | Query result caching                                         |

### Frontend Stack

| Component             | Technology                          | Purpose                                                        |
| --------------------- | ----------------------------------- | ------------------------------------------------------------- |
| **Framework**         | React 18+ with TypeScript           | Component-based UI with type safety                           |
| **State Management**  | React hooks *(Zustand planned)*     | Local component state today; Zustand store arrives with Day 2 |
| **Styling**           | CSS Modules + design tokens         | Glass theme, 5 palettes; **Tailwind/shadcn removed** (locked per MASTERPLAN D1) |
| **Visualization**     | Recharts *(Day 2)*                  | React-native charts with declarative API                     |
| **Real-time Updates** | NDJSON stream over `/query` (+ `/ws`) | Live per-agent progress during query processing              |

### Training Infrastructure

| Component              | Technology                     | Purpose                                  |
| ---------------------- | ------------------------------ | ---------------------------------------- |
| **Training Framework** | Unsloth                        | 2x faster training, 70% less VRAM        |
| **Training Platform**  | Google Colab (Free T4)         | QLoRA on 16GB VRAM, ~3 hours per adapter |
| **Training Datasets**  | gretelai/synthetic_text_to_sql | 105K high-quality SQL pairs              |
| **Supplementary Data** | b-mc2/sql-create-context       | 78K Spider-derived examples              |
| **Validation Set**     | Spider Dev                     | Standard NL2SQL benchmark                |
| **Export Format**      | GGUF (Q4_K_M)                  | llama.cpp compatible with LoRA support   |

### Development & Deployment

| Component            | Technology                                  | Purpose                               |
| -------------------- | ------------------------------------------- | ------------------------------------- |
| **Containerization** | Docker + Docker Compose                     | Reproducible environment              |
| **Version Control**  | Git + GitHub                                | Source management, CI/CD              |
| **IDE**              | Visual Studio Code                          | Python, TypeScript, Docker extensions |
| **Testing**          | pytest (Python), Jest (TypeScript)          | Unit and integration testing          |
| **Code Quality**     | ruff, black (Python), ESLint, Prettier (TS) | Linting and formatting                |

---

## Architecture Diagram (Completed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │Query Builder│  │ Visualization│  │  Progress   │  │  Session  │  │
│  │  (Keywords) │  │  (Recharts)  │  │  Indicator  │  │  Library  │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └───────────┘  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ REST API + WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Multi-Agent Orchestrator                  │   │
│  │         (Workflow routing, state management, progress)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       │              │              │              │                │
│  ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐              │
│  │ Context │   │  Query  │   │   SQL   │   │ Verify  │              │
│  │ Manager │   │ Under-  │   │Generator│   │  Agent  │              │
│  │  Agent  │   │standing │   │  Agent  │   │         │              │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘              │
│       │              │              │              │                │
│  ┌────▼──────────────▼──────────────▼──────────────▼────┐           │
│  │              LLM Service (Adapter Controller)         │          │
│  │   • Manages llama.cpp server connection               │          │
│  │   • LoRA hot-swap via /lora-adapters API (<100ms)     │          │
│  │   • Routes requests to appropriate adapter            │          │
│  └──────────────────────────┬───────────────────────────┘           │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ HTTP API (localhost:7860)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      llama.cpp Server                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Base Model: Qwen2.5-Coder-3B-Instruct (Q4_K_M) ~2GB VRAM     │  │
│  │                                                               │  │
│  │  LoRA Adapters (preloaded, switched by demand, in  order):    │  │
│  │  ├── query_understanding.gguf  (~30MB)                        │  │
│  │  ├── clarification.gguf        (~30MB)                        │  │
│  │  ├── sql_generator.gguf        (~30MB)                        │  │
│  │  └── verification.gguf         (~30MB)                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
        │                                           │
        ▼                                           ▼
┌───────────────────┐                    ┌────────────────────┐
│    ChromaDB       │                    │  SQLite/PostgreSQL │
│  (Context Store)  │                    │  (Sessions + Meta) │
└───────────────────┘                    └────────────────────┘
```

### Local Inference Setup Guide

The system runs a local Qwen2.5-Coder-3B-Instruct model through a `llama-server` (llama.cpp) instance.
`start.py` locates the `llama-server` binary from your winget install or `PATH`, and loads the GGUF model
from `models/` at the repo root.

1. **Install Python 3.10+** from [python.org](https://www.python.org/downloads/).

2. **Install the `llama-server` binary** — the easiest route on Windows is winget:
   ```powershell
   winget install ggml.llamacpp
   ```
   (Alternatively, build llama.cpp yourself and put `llama-server` on your `PATH`.)

3. **Place the GGUF model** at the repo root under `models/`:
   ```
   models/qwen2.5-coder-3b-instruct-q4_k_m.gguf
   ```
   Download it from Hugging Face (`Qwen/Qwen2.5-Coder-3B-Instruct-GGUF`, the `q4_k_m` quant).
   The `models/` directory and `*.gguf` files are gitignored.

4. **Install project dependencies**:
   ```powershell
   pip install -r backend/requirements.txt
   cd frontend; npm install
   ```

5. **Run everything** from the repo root:
   ```powershell
   python start.py
   ```
   This launches the llama.cpp server, the FastAPI backend (port 5000), and the Vite frontend (port 5173).
