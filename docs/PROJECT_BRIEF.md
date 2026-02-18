# IDI (Intelligent Database Interface) - Project Brief

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

| Component | Technology | Specification |
|-----------|------------|---------------|
| **Base Model** | Qwen2.5-Coder-3B-Instruct | Best SQL performance at 3B scale |
| **Quantization** | Q4_K_M (GGUF format) | ~2GB VRAM, 25-35 tokens/sec on GTX 1650 |
| **Inference Engine** | llama.cpp | Native LoRA hot-swap via `/lora-adapters` API |
| **Fine-tuning Method** | LoRA (Low-Rank Adaptation) | Task-specific adapters (~20-50MB each) |
| **Training Platform** | Google Colab + Unsloth | Free T4 GPU, QLoRA support, 2-4 hours per adapter |

### LoRA Adapters (Task-Specific Fine-Tuning)

| Adapter | Purpose | Training Dataset | Priority |
|---------|---------|------------------|----------|
| **query_understanding.gguf** | Intent classification, entity extraction | Synthesized from SQL datasets | High |
| **clarification.gguf** | Generate follow-up questions | Custom dialogue dataset | Optional |
| **sql_generator.gguf** | NL → SQL translation | `gretelai/synthetic_text_to_sql` (15-20K samples) | Critical |
| **verification.gguf** | SQL error detection and correction | Self-generated error corpus | Medium |

### Backend Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | Async support, auto-generated OpenAPI docs, WebSocket native |
| **LLM Service** | llama.cpp server | Model hosting with LoRA adapter management |
| **Vector Database** | ChromaDB | Context embeddings storage and semantic search |
| **Session Storage** | SQLite (dev) / PostgreSQL (prod) | Session persistence with JSONB for flexible data |
| **Cache Layer** | In-memory / Redis (optional) | Query result caching |

### Frontend Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | React 18+ with TypeScript | Component-based UI with type safety |
| **State Management** | Zustand | Minimal boilerplate, React 18 compatible |
| **UI Components** | shadcn/ui | Accessible, customizable Tailwind components |
| **Visualization** | Recharts | React-native charts with declarative API |
| **Real-time Updates** | WebSocket | Progress indicators during query processing |

### Training Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Training Framework** | Unsloth | 2x faster training, 70% less VRAM |
| **Training Platform** | Google Colab (Free T4) | QLoRA on 16GB VRAM, ~3 hours per adapter |
| **Training Datasets** | gretelai/synthetic_text_to_sql | 105K high-quality SQL pairs |
| **Supplementary Data** | b-mc2/sql-create-context | 78K Spider-derived examples |
| **Validation Set** | Spider Dev | Standard NL2SQL benchmark |
| **Export Format** | GGUF (Q4_K_M) | llama.cpp compatible with LoRA support |

### Development & Deployment

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker + Docker Compose | Reproducible environment |
| **Version Control** | Git + GitHub | Source management, CI/CD |
| **IDE** | Visual Studio Code | Python, TypeScript, Docker extensions |
| **Testing** | pytest (Python), Jest (TypeScript) | Unit and integration testing |
| **Code Quality** | ruff, black (Python), ESLint, Prettier (TS) | Linting and formatting |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │Query Builder│  │ Visualization│  │  Progress   │  │  Session  │ │
│  │  (Keywords) │  │  (Recharts)  │  │  Indicator  │  │  Library  │ │
│  └─────────────┘  └──────────────┘  └─────────────┘  └───────────┘ │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ REST API + WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Multi-Agent Orchestrator                   │   │
│  │         (Workflow routing, state management, progress)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       │              │              │              │                 │
│  ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐            │
│  │ Context │   │  Query  │   │   SQL   │   │ Verify  │            │
│  │ Manager │   │ Under-  │   │Generator│   │  Agent  │            │
│  │  Agent  │   │standing │   │  Agent  │   │         │            │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘            │
│       │              │              │              │                 │
│  ┌────▼──────────────▼──────────────▼──────────────▼────┐          │
│  │              LLM Service (Adapter Controller)         │          │
│  │   • Manages llama.cpp server connection               │          │
│  │   • LoRA hot-swap via /lora-adapters API (<100ms)     │          │
│  │   • Routes requests to appropriate adapter            │          │
│  └──────────────────────────┬───────────────────────────┘          │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ HTTP API (localhost:8080)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      llama.cpp Server                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Base Model: Qwen2.5-Coder-3B-Instruct (Q4_K_M) ~2GB VRAM     │  │
│  │                                                                │  │
│  │  LoRA Adapters (preloaded, switched at runtime, in execution order): │  │
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

---

## Hardware Requirements

### Minimum (Development/Demo)

| Component | Specification |
|-----------|---------------|
| **GPU** | GTX 1650 4GB VRAM (or equivalent) |
| **RAM** | 16GB DDR4 |
| **CPU** | Intel Core i7 9th Gen (or equivalent) |
| **Storage** | 20GB free space (models + data) |
| **OS** | Windows 10/11 |

### Inference Performance (GTX 1650)

| Metric | Value |
|--------|-------|
| VRAM Usage | ~2.5GB (base model + active adapter) |
| Token Generation | 25-35 tokens/second |
| Simple Query Latency | 2-5 seconds |
| Complex Query Latency | 5-15 seconds |
| LoRA Switch Time | <100ms |

### Recommended (Production)

| Component | Specification |
|-----------|---------------|
| **GPU** | RTX 3060 8GB+ VRAM |
| **RAM** | 32GB DDR4 |
| **CPU** | Intel Core i7 12th Gen+ |
| **Storage** | SSD with 50GB+ free space |

---

## Objectives

### General Objective

Design, develop, and evaluate IDI as a modular multi-agent NL2SQL system that enables non-technical executives to extract statistical insights from relational databases, achieving >75% query correctness while operating on consumer hardware (GTX 1650, 4GB VRAM).

> **Development period:** 2026‑1S Semester (February 2 – May 30, 2026).

### Specific Objectives

1. **Requirements Analysis**: Comprehensive analysis identifying functional/non-functional requirements, success criteria, and evaluation metrics
2. **System Design**: Modular architecture specification with LoRA adapter strategy, communication protocols, and technology stack validation
3. **Solution Development**: Implementation of seven core modules with LoRA fine-tuning, FastAPI backend, and React frontend
4. **Results Analysis**: Performance evaluation through quantitative benchmarking (Spider, BIRD) and qualitative user studies

---

## LoRA Fine-Tuning Strategy

### Training Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Training Data   │────▶│  Google Colab    │────▶│   GGUF Export    │
│  (HuggingFace)   │     │  (Unsloth+QLoRA) │     │  (llama.cpp)     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │  Local Inference │
                                                  │  (GTX 1650)      │
                                                  └──────────────────┘
```

### Training Configuration

```python
# Unsloth LoRA Configuration
lora_config = {
    "r": 16,                    # LoRA rank
    "lora_alpha": 32,           # Scaling factor
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj"       # MLP
    ],
    "bias": "none",
    "task_type": "CAUSAL_LM"
}

# Training Arguments
training_args = {
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "fp16": True,               # QLoRA 4-bit on Colab
    "logging_steps": 10,
    "output_dir": "./results"
}
```

### Expected Accuracy Improvement

| Agent | Base Model | With LoRA | Target |
|-------|------------|-----------|--------|
| SQL Generator | 55-65% | 70-80% | **75%+** |
| Query Understanding | ~60% | 75-85% | **80%+** |
| Verification | ~70% | 85-92% | **88%+** |

---

## Development Timeline (2026‑1S Semester: Feb 2 – May 30)

*Schedule compressed to ensure project completion two weeks before semester end (target: May 16, 2026).*  

### Phase 1: Foundation (Weeks 1-4, Feb 2 – Feb 29)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1-2 | Requirements & Design | SRS document, architecture diagrams, benchmark selection |
| 3-4 | Infrastructure Setup | Colab training environment, llama.cpp local setup, FastAPI scaffold |

### Phase 2: Model Training (Weeks 5-8, Mar 1 – Mar 28)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 5 | SQL Generator LoRA | Trained adapter, Spider validation results |
| 6 | Query Understanding LoRA | Trained adapter, intent classification tests |
| 7 | Verification LoRA | Trained adapter, error detection benchmarks |
| 8 | Integration Testing | All adapters working with hot-swap |

### Phase 3: Application Development (Weeks 9-12, Mar 29 – Apr 25)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 9 | FastAPI Backend | Complete API with orchestrator |
| 10 | React Frontend | Query builder, visualization dashboard |
| 11 | Session Management | Save/load/search sessions |
| 12 | End-to-end Testing | Full pipeline validation |

### Phase 4: Evaluation (Weeks 13-16, Apr 26 – May 23; target completion by May 16)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 13-14 | Quantitative Evaluation | Spider/BIRD benchmarks, latency metrics |
| 15 | User Study | SUS questionnaire, task success rates |
| 16 | Documentation | Thesis writing, final presentation |

> **Note:** the timeline is designed to wrap up by **Week 14** (mid‑May) so that there are two weeks remaining before the end of the 2026‑1S semester.
---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **SQL Execution Accuracy** | >75% | Spider dev set |
| **Query Latency (simple)** | <5 seconds | Single table queries |
| **Query Latency (complex)** | <15 seconds | Multi-join queries |
| **LoRA Switch Time** | <100ms | Adapter hot-swap |
| **VRAM Usage** | <3.5GB | With active adapter |
| **Usability Score** | >70 SUS | User study |
| **Verification Accuracy** | >88% | Error detection rate |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LoRA accuracy below target | Medium | High | Increase training data, adjust hyperparameters |
| GTX 1650 VRAM insufficient | Low | High | Already validated: 3B Q4_K_M fits in ~2.5GB |
| llama.cpp LoRA issues | Low | Medium | Fallback to Ollama Modelfiles |
| Colab session limits | Medium | Low | Split training across multiple sessions |
| Integration complexity | Medium | Medium | Incremental testing, clear interfaces |

---

## Project Repository Structure

```
idi-project/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Configuration settings
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── query.py        # Query processing endpoints
│   │   │   │   ├── session.py      # Session management
│   │   │   │   └── health.py       # Health checks
│   │   │   └── websocket.py        # Progress updates
│   │   ├── services/
│   │   │   ├── llm_service.py      # LoRA adapter management
│   │   │   ├── orchestrator.py     # Multi-agent coordination
│   │   │   └── sql_executor.py     # Database execution
│   │   ├── agents/
│   │   │   ├── query_understanding.py
│   │   │   ├── sql_generator.py
│   │   │   ├── verification.py
│   │   │   └── clarification.py
│   │   └── prompts/                # Prompt templates per agent
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── QueryBuilder/
│   │   │   ├── Visualization/
│   │   │   ├── ProgressIndicator/
│   │   │   └── SessionLibrary/
│   │   ├── services/
│   │   ├── stores/                 # Zustand state management
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
│
├── models/                         # Base model files
│   └── qwen2.5-coder-3b-instruct-q4_k_m.gguf
│
├── adapters/                       # LoRA adapter files
│   ├── sql_generator.gguf
│   ├── query_understanding.gguf
│   ├── verification.gguf
│   └── clarification.gguf
│
├── training/                       # Colab notebooks
│   ├── train_sql_generator.ipynb
│   ├── train_query_understanding.ipynb
│   ├── train_verification.ipynb
│   └── data_preparation.ipynb
│
├── data/
│   ├── benchmarks/                 # Spider, BIRD test sets
│   └── synthetic/                  # Custom training data
│
├── docs/
│   ├── IDI_Project_EN_Part1.md
│   ├── IDI_Project_EN_Part2-1.md
│   ├── IDI_Project_EN_Part2-2.md
│   └── Propuesta_Proyecto_ES.md
│
├── scripts/
│   ├── start_llama_server.ps1     # Windows startup script
│   ├── download_models.py
│   └── export_lora_to_gguf.py
│
├── docker-compose.yml
└── README.md
```

---

## Quick Start Commands

### 1. Download Base Model

```powershell
# Using Hugging Face CLI
huggingface-cli download Qwen/Qwen2.5-Coder-3B-Instruct-GGUF `
    qwen2.5-coder-3b-instruct-q4_k_m.gguf `
    --local-dir ./models
```

### 2. Start llama.cpp Server (Windows)

```powershell
# Start with all LoRA adapters preloaded
llama-server.exe `
    -m .\models\qwen2.5-coder-3b-instruct-q4_k_m.gguf `
    --lora .\adapters\sql_generator.gguf `
    --lora .\adapters\query_understanding.gguf `
    --lora .\adapters\verification.gguf `
    --lora-init-without-apply `
    --host 127.0.0.1 --port 8080 `
    -c 4096 -ngl 99
```

### 3. Start FastAPI Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start React Frontend

```powershell
cd frontend
npm install
npm run dev
```

---

## References

### Models & Training
- [Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF)
- [Unsloth Documentation](https://docs.unsloth.ai/)
- [llama.cpp LoRA Documentation](https://github.com/ggerganov/llama.cpp)

### Datasets
- [gretelai/synthetic_text_to_sql](https://huggingface.co/datasets/gretelai/synthetic_text_to_sql) - 105K samples
- [b-mc2/sql-create-context](https://huggingface.co/datasets/b-mc2/sql-create-context) - 78K samples
- [Spider Benchmark](https://yale-lily.github.io/spider)

### Frameworks
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Recharts](https://recharts.org/)
- [ChromaDB](https://www.trychroma.com/)

---

## Contact & Resources

**Institution**: Universidad Nacional de Colombia  
**Program**: Computer and Systems Engineering  
**Project Type**: Thesis  

**Repository**: intelligent-database-interface  
**Documentation**: See `/docs` folder for comprehensive technical documentation

---

*This brief summarizes a comprehensive NL2SQL system designed to bridge the gap between executive strategic vision and data-driven validation, enabling conversational database exploration without technical intermediaries—all running locally on consumer hardware.*
