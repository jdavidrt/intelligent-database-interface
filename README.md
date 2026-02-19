# IDI (Intelligent Database Interface)

## Overview

IDI is a modular, multi-agent Natural Language to SQL (NL2SQL) system designed to enable non-technical executives and managers to extract statistical insights from relational databases through natural language queries, without requiring SQL expertise or technical intermediaries.

**Academic Context**: Computer and Systems Engineering Thesis, Universidad Nacional de Colombia

**Author**: Juan David Ramírez Torres (<jdramirezt@unal.edu.co>)
**Semester**: 2026-1S (February 2 – May 30, 2026)

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

| Component             | Technology                | Purpose                                      |
| --------------------- | ------------------------- | -------------------------------------------- |
| **Framework**         | React 18+ with TypeScript | Component-based UI with type safety          |
| **State Management**  | Zustand                   | Minimal boilerplate, React 18 compatible     |
| **UI Components**     | shadcn/ui                 | Accessible, customizable Tailwind components |
| **Visualization**     | Recharts                  | React-native charts with declarative API     |
| **Real-time Updates** | WebSocket                 | Progress indicators during query processing  |

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
                              │ HTTP API (localhost:8080)
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

### Sandbox Setup Guide

To set up the sandbox environment for running the Qwen2.5-Coder-3B-Instruct model using llama.cpp, follow these steps:

1. **Install Required Tools**:
   - **Python 3.10 or higher**: Download and install Python from [python.org](https://www.python.org/downloads/).
   - **Chocolatey**: If not already installed, follow the instructions at [Chocolatey Installation Guide](https://chocolatey.org/install).
   - **CMake**: Install CMake using Chocolatey:
     ```powershell
     choco install cmake -y
     ```
   - **Git**: Install Git using Chocolatey:
     ```powershell
     choco install git -y
     ```
   - **Visual Studio Build Tools**: Download and install the [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/). During installation, ensure you select the "Desktop development with C++" workload.

2. **Clone the llama.cpp Repository**:
   - Open a terminal and navigate to the directory where you want to clone the repository.
   - Run the following command:
     ```powershell
     git clone https://github.com/ggml-org/llama.cpp.git
     ```

3. **Build llama.cpp**:
   - Navigate to the `llama.cpp` directory:
     ```powershell
     cd llama.cpp
     ```
   - Create a `build` directory and navigate into it:
     ```powershell
     mkdir build
     cd build
     ```
   - Run CMake to configure and build the project:
     ```powershell
     cmake ..
     cmake --build . --config Release
     ```

4. **Download the Qwen2.5-Coder-3B-Instruct Model**:
   - Set your Hugging Face token as an environment variable:
     ```powershell
     $env:HUGGINGFACE_TOKEN = "your_huggingface_token"
     ```
   - Download the model:
     ```powershell
     Invoke-WebRequest -Uri "https://huggingface.co/Qwen/Qwen-2.5-Coder-3B-Instruct/resolve/main/qwen-2.5-coder-3b-instruct.q4_k_m.gguf" -Headers @{Authorization = "Bearer $env:HUGGINGFACE_TOKEN"} -OutFile "models/qwen-2.5-coder-3b-instruct.q4_k_m.gguf"
     ```

5. **Run the Sandbox Application**:
   - Start the llama.cpp server:
     ```powershell
     ./server --model models/qwen-2.5-coder-3b-instruct.q4_k_m.gguf --port 8080
     ```
   - Run the sandbox application:
     ```powershell
     python sandbox_app.py
     ```

Ensure all dependencies are installed and properly configured before running the setup script or the sandbox application.
