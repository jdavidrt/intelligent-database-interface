# IDI (Intelligent Database Interface) Development Guide

Development guidelines and commands for the IDI project, a multi-agent NL2SQL system designed for executive statistical insights.

## Strategic Project Context

### 🎯 Purpose & Audience
- **Target User**: Non-technical executives and managers.
- **Goal**: Transform natural language queries into verified statistical insights and SQL without technical intermediaries.
- **Value Proposition**: Reduce decision latency, eliminate communication friction between business and technical layers, and optimize resource allocation.

### 🏗️ Guiding Principles
- **Local-First over Cloud**: Prioritize local execution to minimize costs and protect sensitive data.
- **Executive-First UX**: Prioritize clarity, ambiguity resolution, and automatic visualization.
- **Fail-Safe Design**: Never execute unverified SQL; maintain a three-layer verification chain (Syntax → Semantic → Sanity).
- **Hard-Constraint targets**: Target consumer-grade hardware (16GB RAM, 4GB VRAM/GTX 1650 class).

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
- **Run dev server**: `uvicorn backend.main:app --reload` (from workspace root)
- **Run llama.cpp server**: See `README.md` for build instructions, then run `./server --model models/qwen-2.5-coder-3b-instruct.q4_k_m.gguf --port 8080`

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
- **Styling**: Tailwind CSS + shadcn/ui.
- **Design Aesthetic**: High-density, glass-themed, premium look-and-feel.

## Assistant Orientation
- **Minimize Dependencies**: Avoid adding new heavy libraries; leverage existing tech stack.
- **Functional Modularity**: Keep agents decoupled; changes in one should not break the orchestration logic.
- **Performance Aware**: Be mindful of VRAM usage; assume the 4GB limit for the inference engine.
- **Verification Priority**: When implementing features, always consider how they will be verified (both automated and via the Verification Agent).
