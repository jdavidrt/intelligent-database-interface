# IDI (Intelligent Database Interface) - Project Brief

## Overview

IDI is a modular, multi-agent Natural Language to SQL (NL2SQL) system designed to enable non-technical executives and managers to extract statistical insights from relational databases through natural language queries, without requiring SQL expertise or technical intermediaries.

**Academic Context**: Computer and Systems Engineering Thesis, Universidad Nacional de Colombia

## The Problem

Modern executives possess strategic vision but lack SQL knowledge to validate intuitions with data. Current barriers include:

- **85% of organizational decision-makers lack SQL proficiency**, creating dependency bottlenecks on data analysts
- **Decision latency**: Strategic decisions delayed hours or days awaiting technical query execution
- **Resource misallocation**: Skilled data professionals occupied with routine reporting tasks
- **Communication friction**: Semantic gaps between business questions and technical implementations

## The Solution

IDI transforms ambiguous natural language questions into verified statistical insights through:

1. **Context Acquisition**: Structured surveys capture enterprise-specific domain knowledge, business logic, and terminology
2. **Ambiguity Resolution**: Keyword-guided interfaces combined with clarification dialogues resolve underspecification
3. **Multi-Agent Architecture**: Six specialized modules orchestrate interpretation, SQL generation, and error correction
4. **Three-Layer Verification**: Syntax, semantic, and sanity checking ensures >90% query correctness
5. **Automatic Visualization**: Intelligent chart selection and rendering for trend identification and analysis
6. **Local Deployment**: Optimized for consumer hardware (16GB RAM, 8GB VRAM) to minimize cloud dependency and costs

## System Architecture

### Six Core Modules

1. **Context Manager Agent**: Acquires and maintains enterprise-specific domain knowledge through surveys and embeddings
2. **Query Understanding Agent**: Parses natural language, detects ambiguities, and generates clarification questions
3. **SQL Generator Agent**: Translates structured intent into executable SQL using fine-tuned language models
4. **Verification Agent**: Validates correctness through three-layer checking (syntax → semantic → sanity)
5. **Visualization Engine**: Automatically selects and renders appropriate charts based on result structure
6. **Multi-Agent Orchestrator**: Coordinates dynamic workflow routing and manages conversation state

### Key Design Principles

- **Modular Architecture**: Separation of concerns enables independent component evolution
- **Fail-Safe Design**: Verification layer prevents execution of malformed queries
- **Stateful Context**: Session management enables multi-turn conversational queries
- **Local-First**: Eliminates per-query API fees and keeps sensitive data on-premises

## Objectives

### General Objective

Design, develop, and evaluate IDI as a modular multi-agent NL2SQL system that enables non-technical executives to extract statistical insights from relational databases, achieving >90% query correctness while operating on local consumer hardware.

### Specific Objectives

1. **Requirements Analysis**: Comprehensive analysis identifying functional/non-functional requirements, success criteria, and evaluation metrics
2. **System Design**: Modular architecture specification with component responsibilities, communication protocols, and technology stack selection
3. **Solution Development**: Implementation of six core modules with synthetic training data, model fine-tuning, and user interface
4. **Results Analysis**: Performance evaluation through quantitative benchmarking and qualitative user studies

## Technology Stack

### Language Models
- **Query Understanding**: Mistral 7B Instruct (efficient, strong instruction-following)
- **SQL Generation**: Code Llama 13B Instruct or DeepSeek Coder 6.7B (optimized for code generation)
- **Fine-tuning**: LoRA/QLoRA for parameter-efficient adaptation

### Data Storage
- **Vector Database**: ChromaDB or FAISS (context embeddings and semantic search)
- **Relational Database**: PostgreSQL/MySQL (target databases and metadata)
- **Cache Layer**: Redis (query results and generated SQL)

### Orchestration & Visualization
- **Multi-Agent Framework**: LangGraph or AutoGen
- **Visualization**: Plotly.js or Recharts (interactive charts)
- **Interface**: Web-based UI with query builder and dashboard

## Methodology

**Approach**: Design Science Research (DSR) with Agile-inspired incremental development

### Development Sprints (16 weeks)

- **Sprint 1 (Weeks 1-4)**: Requirements analysis and system design
- **Sprint 2 (Weeks 5-8)**: Core infrastructure and Context Manager implementation
- **Sprint 3 (Weeks 9-12)**: SQL generation and verification modules
- **Sprint 4 (Weeks 13-16)**: Integration, visualization, and comprehensive evaluation

### Evaluation Metrics

**Quantitative**:
- Execution Accuracy (EX): >90% target
- Exact Match Accuracy (EM): SQL matching gold-standard
- Latency: Mean and 90th percentile processing time
- Verification Performance: Error detection rate and false positives
- Resource Utilization: RAM, VRAM, CPU usage

**Qualitative**:
- System Usability Scale (SUS): >70 "good" threshold
- Task Success Rate: Percentage of realistic tasks completed
- Expert Review: SQL quality assessment by database administrators

### Benchmark Datasets

- **Spider**: 10,181 queries across 200 databases (cross-domain assessment)
- **BIRD**: Enterprise-scale benchmark with complex schemas
- **Synthetic Data**: Domain-specific query-SQL pairs for fine-tuning

## Innovation & Contribution

### Technical Innovations

1. **Novel Context Acquisition**: Systematic domain knowledge acquisition through structured surveys (vs. generic few-shot prompting)
2. **Hybrid Ambiguity Resolution**: Proactive keyword guidance + conversational clarification (vs. post-hoc error correction)
3. **Multi-layer Verification**: Three-stage semantic verification pipeline (vs. simple syntax checking)
4. **Resource Optimization**: Enterprise-grade NL2SQL on consumer hardware (vs. cloud-dependent solutions)

### Expected Impact

- **Democratization**: Enable millions of non-technical managers to access organizational data independently
- **Cost Efficiency**: Reduce analyst time on routine queries by 30%, reallocating to high-value tasks
- **Decision Speed**: Reduce decision-making cycles by 50%, correlating with 15-20% revenue growth potential
- **Academic Contribution**: Advances in context acquisition, verification pipelines, and resource-constrained deployment

## Differentiators vs. Existing Solutions

| Aspect | Existing Solutions | IDI Innovation |
|--------|-------------------|----------------|
| Domain Knowledge | Few-shot prompting with examples | Structured survey-based context acquisition |
| Ambiguity Handling | Post-hoc clarification after failure | Proactive keyword guidance + dialogue |
| Verification | Syntax checking or execution testing | Three-layer semantic verification |
| Multi-turn | Session history in prompt | Explicit conversation state management |
| Visualization | External BI tools | Integrated automatic chart selection |
| Resource Efficiency | Cloud-dependent (API calls) | Local deployment on consumer hardware |

## Use Case Example

**Query**: "Show me sales performance last quarter"

**System Flow**:
1. Detects ambiguity: "last quarter" undefined
2. Retrieves fiscal calendar from context
3. Prompts clarification: "Which quarter? [Q1 2024 | Q2 2024 | Q3 2024 | Q4 2024]"
4. User selects: "Q3 2024"
5. Generates SQL with monthly aggregation
6. Verifies syntax, semantics, and result sanity
7. Renders line chart showing monthly sales trend
8. Displays KPI cards: Q3 total ($4.93M), QoQ growth (+8%)

## Success Criteria

1. **Accuracy**: >90% execution accuracy on benchmark datasets
2. **Usability**: System Usability Scale (SUS) score >70
3. **Performance**: Query processing <3 seconds for simple queries
4. **Deployment**: Successful operation on consumer hardware (16GB RAM, 8GB VRAM)
5. **Verification**: >95% error detection rate with <5% false positives

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM hallucination | High | Three-layer verification + fine-tuning |
| Resource constraints | Medium | Model quantization (4-bit), modular architecture |
| Schema complexity | High | Structured context acquisition, metadata augmentation |
| User adoption | Medium | Keyword-guided interface, automatic visualization |
| Evaluation validity | Medium | Multiple benchmarks (Spider, BIRD), user studies |

## Timeline Summary

- **Phase 1** (4 weeks): Requirements & Design
- **Phase 2** (4 weeks): Core Infrastructure
- **Phase 3** (4 weeks): SQL Generation & Verification
- **Phase 4** (4 weeks): Integration & Evaluation

**Total Duration**: 16 weeks

## Contact & Resources

**Institution**: Universidad Nacional de Colombia
**Program**: Computer and Systems Engineering
**Project Type**: Thesis

**Repository**: intelligent-database-interface
**Documentation**: IDI_Project_EN.md (comprehensive technical documentation)

---

*This brief summarizes a comprehensive NL2SQL system designed to bridge the gap between executive strategic vision and data-driven validation, enabling conversational database exploration without technical intermediaries.*
