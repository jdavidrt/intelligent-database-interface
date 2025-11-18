# IDI (Intelligent Database Interface): Contextual NL2SQL System for Executive Decision Support

## Project Documentation - Computer and Systems Engineering Thesis
### Universidad Nacional de Colombia

---

## Executive Summary

**IDI (Intelligent Database Interface): Bridging Intent and Intelligence Through Contextual NL2SQL**

Modern executives and managers possess strategic vision but lack SQL knowledge to validate intuitions with data. IDI dissolves this barrier through a modular, multi-agent NL2SQL (Natural Language to SQL) system that transforms ambiguous questions into verified statistical insights. Unlike monolithic solutions, it acquires domain knowledge through structured surveys, resolves ambiguity via keyword-guided interfaces, and ensures correctness through three-layer verification. Agent-based workflows dynamically orchestrate interpretation linking, SQL generation, and error correction. The system presents statistics, not prescriptions, accompanied by automatic visualizations. This architecture democratizes data access while maintaining enterprise reliability, allowing managers to explore databases conversationally without technical intermediaries.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Problem Statement](#2-problem-statement)
3. [Justification](#3-justification)
4. [State of the Art](#4-state-of-the-art)
5. [Theoretical Framework](#5-theoretical-framework)
6. [Objectives](#6-objectives)
7. [Methodology](#7-methodology)
8. [System Architecture](#8-system-architecture)

**For sections 9-15, see IDI_Project_EN_Part2.md**

---

## 1. Introduction

### 1.1 Context

In the contemporary data-driven business landscape, organizations accumulate vast volumes of information within relational database management systems (RDBMS). These repositories contain critical insights for strategic decision-making, operational optimization, and competitive advantage. However, a significant barrier persists: the technical expertise required to extract meaningful information through Structured Query Language (SQL) remains beyond the reach of most business executives and managers.

Studies indicate that approximately 85% of organizational decision-makers lack SQL proficiency, creating a dependency bottleneck on data analysts and IT departments for routine data queries (Luo et al., 2025). This technical gap manifests in several organizational inefficiencies:

- **Decision latency**: Strategic decisions delayed hours or days awaiting technical query execution
- **Resource misallocation**: Highly skilled data professionals occupied with routine reporting tasks
- **Opportunity cost**: Real-time strategic pivots impossible due to data access constraints
- **Communication friction**: Semantic gaps between business questions and technical implementations

The emergence of Large Language Models (LLMs) and Natural Language Processing (NLP) technologies offers unprecedented opportunities to bridge this divide through Natural Language to SQL (NL2SQL) systems. These systems promise to democratize database access by translating conversational queries into executable SQL statements, effectively removing the technical barrier that separates business intuition from data validation.

### 1.2 Evolution of NL2SQL

The NL2SQL research domain has evolved through four distinct paradigmatic eras:

1. **Statistical Language Model Era (1990s-2016)**: Rule-based systems and N-gram approaches achieved limited success on narrow domains with rigid syntactic patterns.

2. **Neural Language Model Era (2017-2018)**: Introduction of LSTMs and attention mechanisms, culminating in the seminal Spider benchmark (Yu et al., 2018), establishing standardized cross-domain evaluation.

3. **Pre-trained Language Model Era (2018-2023)**: Transformer-based models (BERT, T5) elevated accuracy to 70-80% on complex benchmarks through transfer learning and schema encoding techniques.

4. **Large Language Model Era (2023-Present)**: Models like GPT-4, Claude, and LLaMA demonstrate >95% accuracy on domain-specific tasks when properly contextualized, prompting commercial integration by database vendors (Luo et al., 2025).

Despite these advances, enterprise deployment remains challenging due to domain knowledge gaps, schema complexity, ambiguity handling, and trustworthiness concerns—challenges that IDI specifically addresses through modular architecture and contextual awareness.

### 1.3 Project Scope

This thesis project proposes the design, development, and evaluation of IDI (Intelligent Database Interface), a comprehensive NL2SQL system tailored for executive decision support. The system integrates six specialized modules orchestrated through agentic workflows:

1. **Context Manager Agent**: Acquires and maintains enterprise-specific domain knowledge
2. **Query Understanding Agent**: Parses natural language and detects ambiguities
3. **SQL Generator Agent**: Translates structured intent into executable SQL
4. **Verification Agent**: Validates correctness through three-layer checking
5. **Visualization Engine**: Automatically renders statistical insights
6. **Multi-Agent Orchestrator**: Coordinates dynamic workflow routing

The project emphasizes practical deployment considerations, including resource constraints (local execution on consumer hardware), cost efficiency (minimal cloud dependency), and extensibility (modular architecture enabling component evolution).

---

## 2. Problem Statement

### 2.1 Primary Problem

**How can non-technical executives and managers access complex relational databases to extract statistical insights for decision-making without requiring SQL expertise or technical intermediaries, while ensuring query correctness and result interpretability?**

### 2.2 Secondary Problems

1. **Domain Knowledge Gap**: General-purpose LLMs lack enterprise-specific schema understanding, business logic, and domain terminology, leading to incorrect query generation for specialized contexts.

2. **Natural Language Ambiguity**: Executive queries often contain underspecification (missing time ranges, unclear entities), synonymy (multiple terms for same concept), and context-dependence (referencing previous results), complicating semantic parsing.

3. **Schema Complexity**: Enterprise databases feature distributed architectures, nested table structures, multi-dimensional data (arrays within columns), and complex join relationships requiring expert-level SQL knowledge.

4. **Multi-turn Dialogue Limitations**: Exploratory data analysis requires conversational sequences with context preservation, entity tracking, and progressive query refinement—capabilities absent in single-shot NL2SQL systems.

5. **SQL Correctness Verification**: Generated queries may contain semantic errors (wrong aggregations, incorrect joins, missing filters) that produce misleading results, undermining trust and potentially impacting business decisions.

6. **Result Interpretability**: Raw tabular outputs lack visual context for trend identification, comparative analysis, and pattern recognition—requiring automatic visualization selection and rendering.

7. **Computational Resource Constraints**: State-of-the-art LLMs (70B+ parameters) demand extensive GPU resources and cloud API costs, creating barriers for resource-constrained environments.

### 2.3 Research Questions

1. Can a structured context acquisition process (surveys, schema documentation) provide sufficient domain knowledge for accurate NL2SQL in specialized business contexts?

2. Does keyword-guided query construction combined with clarification dialogues effectively resolve natural language ambiguity compared to free-form input?

3. What verification mechanisms are necessary and sufficient to achieve >90% SQL correctness in enterprise scenarios?

4. How can multi-agent architectures improve NL2SQL robustness compared to monolithic end-to-end models?

5. What is the optimal balance between model size, accuracy, and inference latency for local deployment on consumer hardware (16GB RAM, 8GB VRAM)?

---

## 3. Justification

### 3.1 Practical Relevance

**Democratization of Data Access**: Approximately 2.5 million new managers enter the workforce annually in Latin America, most lacking technical database skills (ILO, 2024). IDI enables this demographic to independently validate strategic hypotheses with organizational data, reducing decision latency from days to seconds.

**Cost Efficiency**: Organizations spend an average of 30% of data analyst time on routine reporting queries that could be automated (Gartner, 2023). IDI reallocates these resources to high-value analytical tasks like predictive modeling and causal inference.

**Competitive Advantage**: Real-time data access enables agile strategy adaptation. Case studies show that reducing decision-making cycles by 50% correlates with 15-20% revenue growth in volatile markets (McKinsey, 2024).

### 3.2 Academic Contribution

**Novel Context Acquisition Framework**: While existing research focuses on schema linking and few-shot prompting, IDI introduces systematic domain knowledge acquisition through structured surveys, creating reusable context repositories for enterprise deployment.

**Hybrid Ambiguity Resolution**: Combines keyword-guided interface design (reducing input space) with conversational clarification (handling residual ambiguity)—an understudied approach bridging HCI and NLP.

**Multi-layer Verification Pipeline**: Extends beyond syntax checking to semantic equivalence testing and result sanity validation, addressing the trustworthiness gap identified by Floratou et al. (2024).

**Resource-Constrained Optimization**: Demonstrates feasibility of enterprise-grade NL2SQL on consumer hardware through modular decomposition, challenging the prevailing assumption that accuracy requires massive models.

### 3.3 Alignment with National Development Goals

Colombia's National Development Plan 2022-2026 prioritizes digital transformation and data-driven governance. IDI directly supports:

- **Productive Transformation**: Enabling SMEs to leverage data analytics without hiring specialized personnel
- **Human Capital Development**: Training next-generation engineers in cutting-edge AI/database intersection
- **Technological Sovereignty**: Developing locally-adaptable solutions reducing dependency on foreign SaaS platforms

### 3.4 Timeliness

The confluence of three factors creates unique opportunity:

1. **LLM Maturity**: Open-source models (LLaMA 3, Mistral 7B) now rival commercial APIs in specific domains when fine-tuned, enabling cost-effective local deployment.

2. **Benchmark Availability**: Recent releases (BIRD, Spider 2.0) provide standardized evaluation frameworks for rigorous performance assessment.

3. **Industry Demand**: 78% of enterprise database vendors plan NL2SQL integration by 2026 (DB-Engines Survey, 2024), creating market readiness for academic innovations.

---

## 4. State of the Art

### 4.1 Foundational Work: The NL2SQL Lifecycle

Luo et al. (2025) provide the most comprehensive survey of contemporary NL2SQL techniques, organizing the field into a lifecycle framework encompassing training data synthesis, translation methodologies, evaluation protocols, and debugging approaches. Their taxonomy identifies five difficulty levels—from token-level recognition (solved) to multi-turn dialogues (future frontier)—situating current research at Level 4 (domain knowledge and query recognition).

**Key Insights**:
- Pre-trained language models (BERT, T5) achieve 70-80% accuracy through schema encoding and relation-aware parsing (Wang et al., 2020; Scholak et al., 2021)
- LLM-based solutions (GPT-4, Claude) reach >95% on focused domains via prompt engineering and supervised fine-tuning
- Critical unsolved challenges: trustworthy verification, multi-database federation, cost-efficient inference

**Relevance to IDI**: This work validates our modular approach targeting Level 4 challenges (domain knowledge via context acquisition, ambiguity via guided interfaces) while acknowledging Level 5 (multi-turn) as future work.

### 4.2 Enterprise-Scale Deployment: AWS-Cisco Pattern

Kumar et al. (2025) present a production-tested architecture for enterprise NL2SQL addressing challenges IDI specifically targets:

**Domain-Scoped Prompts**: Reduces prompt complexity by classifying queries into business domains (finance, HR, operations), constructing context from relevant schemas only—reducing LLM attention burden by 60-80%.

**Identifier Pre-resolution**: Separates named entity recognition (NER) from SQL generation by resolving entities (employee names, product IDs) to database keys before query construction, enabling handling of 200+ entities per query.

**Data Abstractions**: Creates temporary views for complex joins and nested structures, allowing LLMs to generate simple set operations (IN, EXISTS) rather than intricate multi-table joins.

**Verification Architecture**: Three-stage validation (syntax → semantic alignment → execution sanity) achieves 98% error detection with <5% false positives.

**Performance Results**: 95% accuracy at 1-3 second latency using lightweight models (Code Llama 13B, Claude Haiku)—demonstrating that architectural optimization supersedes model scale.

**Relevance to IDI**: Direct architectural inspiration for our modular design, verification pipeline, and resource optimization strategy. IDI extends this work through interface-level ambiguity resolution and automatic visualization.

### 4.3 Multi-Agent Frameworks: CHASE-SQL and Alpha-SQL

Recent work explores agent-based decomposition of NL2SQL tasks:

**CHASE-SQL** (Talaei et al., 2024): Contextual Harnessing for Efficient SQL Synthesis using specialized agents for schema pruning, candidate generation, and execution-based ranking. Achieves 89% execution accuracy on Spider benchmark through multi-path reasoning.

**Alpha-SQL** (Li et al., 2025): Zero-shot framework combining LLMs with Monte Carlo Tree Search (MCTS) for autonomous workflow planning. Dynamically selects modules (schema linking, SQL generation, verification) based on contextual reasoning, achieving state-of-the-art results on BIRD benchmark.

**Relevance to IDI**: Validates our multi-agent orchestrator concept. IDI adapts these ideas for enterprise contexts with explicit context management and interface-guided disambiguation.

### 4.4 Gap Analysis

| Aspect | Existing Solutions | IDI Innovation |
|--------|-------------------|----------------|
| **Domain Knowledge** | Few-shot prompting with examples | Structured survey-based context acquisition |
| **Ambiguity Handling** | Post-hoc clarification after failure | Proactive keyword guidance + dialogue |
| **Verification** | Syntax checking or execution testing | Three-layer semantic verification |
| **Multi-turn** | Session history in prompt | Explicit conversation state management |
| **Visualization** | External BI tools | Integrated automatic chart selection |
| **Resource Efficiency** | Cloud-dependent (API calls) | Local deployment on consumer hardware |

---

## 5. Theoretical Framework

### 5.1 Natural Language Processing Foundations

**Semantic Parsing**: The task of mapping natural language utterances to formal meaning representations (Zelle & Mooney, 1996). In NL2SQL, the target formalism is SQL, requiring compositional semantics understanding.

**Schema Linking**: Explicitly connecting NL phrases to database schema elements (tables, columns, values) before SQL generation—a critical sub-task improving accuracy by 15-25% (Lei et al., 2020).

**Attention Mechanisms**: Neural architecture components enabling models to focus on relevant input segments when generating each output token (Vaswani et al., 2017)—fundamental to Transformer-based NL2SQL.

### 5.2 Large Language Model Capabilities

**In-Context Learning**: LLM ability to adapt to tasks from prompt examples without parameter updates—enabling few-shot NL2SQL with 3-5 demonstrations (Brown et al., 2020).

**Chain-of-Thought Reasoning**: Generating intermediate reasoning steps improves complex query handling by 30-40% (Wei et al., 2022)—applicable to multi-join SQL construction.

**Instruction Following**: Fine-tuning on task instructions enhances controllability and reduces hallucination—critical for SQL syntax adherence.

### 5.3 Multi-Agent Systems

**Agent Autonomy**: Agents perceive environments, make decisions, and take actions toward goals—enabling specialized SQL generation agents with defined responsibilities.

**Coordination Mechanisms**: Protocols for agent collaboration including hierarchical (orchestrator-worker) and peer-to-peer patterns—IDI employs hierarchical orchestration.

**Agentic Workflows**: Dynamic task decomposition based on query complexity and context—enabling adaptive processing pipelines.

### 5.4 Human-Computer Interaction Principles

**Guided Input Design**: Constraining input spaces through keywords and structured forms reduces user error and system ambiguity—applicable to query construction interfaces.

**Clarification Dialogues**: Interactive systems that detect uncertainty and solicit user feedback achieve 25-35% higher task success (Schlögl et al., 2016).

**Visualization Effectiveness**: Automatic chart type selection based on data characteristics (time series → line charts, categorical → bar charts) improves comprehension by 40-50% (Mackinlay, 1986).

---

## 6. Objectives

### 6.1 General Objective

**Design, develop, and evaluate IDI (Intelligent Database Interface), a modular multi-agent NL2SQL system that enables non-technical executives to extract statistical insights from relational databases through natural language queries with contextual awareness, ambiguity resolution, and automated verification, achieving >90% query correctness while operating on local consumer hardware.**

### 6.2 Specific Objectives

#### Specific Objective 1: Requirements Analysis

**Conduct comprehensive requirements analysis for an executive-focused NL2SQL system, identifying functional and non-functional requirements, success criteria, and evaluation metrics through literature review, competitive analysis, and stakeholder need assessment.**

**Expected Outcomes**:
- Requirements specification document detailing functional modules, user personas, and use cases
- Benchmark dataset selection justification (Spider, BIRD, or domain-specific alternatives)
- Success metrics definition (accuracy thresholds, latency limits, usability scores)

#### Specific Objective 2: System Design

**Design the IDI modular architecture, specifying component responsibilities, inter-agent communication protocols, data flows, and technology stack selection optimized for local deployment on consumer hardware (16GB RAM, 8GB VRAM).**

**Expected Outcomes**:
- System architecture diagrams (component, deployment, sequence diagrams)
- Module interface specifications (inputs, outputs, APIs)
- Technology stack justification document comparing alternatives (LLM choices, frameworks, databases)
- Context acquisition survey design and metadata schema

#### Specific Objective 3: Solution Development

**Implement the six core IDI modules (Context Manager, Query Understanding, SQL Generator, Verification Agent, Visualization Engine, Multi-Agent Orchestrator) with synthetic training data generation, model fine-tuning pipelines, and user interface components.**

**Expected Outcomes**:
- Functional prototype system with web-based interface
- Fine-tuned LLM models for NL understanding and SQL generation
- Synthetic training dataset (minimum 500 query-SQL pairs)
- Test suite with unit, integration, and system-level tests

#### Specific Objective 4: Results Analysis

**Evaluate IDI performance through quantitative benchmarking (execution accuracy, latency, verification effectiveness) and qualitative assessment (user study, expert review), comparing results against baseline methods and identifying improvement opportunities.**

**Expected Outcomes**:
- Performance evaluation report with statistical significance testing
- User study results (task success rate, System Usability Scale scores)
- Comparative analysis against existing solutions (Tableau Ask Data, Power BI Q&A)
- Recommendations for system enhancement and future work

---

## 7. Methodology

### 7.1 Research Design

This project follows a **Design Science Research (DSR)** methodology (Hevner et al., 2004), emphasizing artifact creation and evaluation:

1. **Problem Identification**: Characterized through literature review and need assessment
2. **Solution Design**: Architectural and algorithmic innovation addressing identified challenges
3. **Artifact Development**: Functional prototype implementation
4. **Artifact Evaluation**: Empirical performance assessment and expert validation
5. **Communication**: Thesis documentation and potential publication

### 7.2 Development Methodology

**Agile-inspired Incremental Development**: Four 4-week sprints aligned with specific objectives, each delivering demonstrable functionality:

- **Sprint 1 (Weeks 1-4)**: Requirements analysis and design
- **Sprint 2 (Weeks 5-8)**: Core infrastructure and Context Manager
- **Sprint 3 (Weeks 9-12)**: SQL generation and verification modules
- **Sprint 4 (Weeks 13-16)**: Integration, visualization, and evaluation

Each sprint includes:
- Planning: Task breakdown and acceptance criteria definition
- Development: Implementation and unit testing
- Review: Functionality demonstration and feedback incorporation
- Retrospective: Process improvement identification

### 7.3 Data Collection

**Benchmark Datasets**: Public NL2SQL benchmarks for standardized evaluation:
- **Spider** (Yu et al., 2018): 10,181 queries across 200 databases for cross-domain assessment
- **BIRD** (Li et al., 2023): Enterprise-scale benchmark with complex schemas and queries
- **Domain-specific alternative**: If available, sector-focused dataset (e.g., finance, healthcare)

**Synthetic Data Generation**: For domain adaptation and fine-tuning:
- Rule-based templates instantiated with schema-specific values
- LLM-driven paraphrasing for linguistic diversity
- Quality validation through execution testing

**User Study Data**: Qualitative evaluation through task-based assessment with 10-15 participants (if feasible within constraints).

### 7.4 Evaluation Approach

**Quantitative Metrics**:
1. **Execution Accuracy (EX)**: Percentage of generated queries producing correct results
2. **Exact Match Accuracy (EM)**: Percentage matching gold-standard SQL exactly
3. **Verification Performance**: Error detection rate (recall) and false positive rate (precision)
4. **Latency**: Mean and 90th percentile query processing time
5. **Resource Utilization**: RAM, VRAM, CPU usage during inference

**Qualitative Assessment**:
1. **System Usability Scale (SUS)**: Standardized 10-item questionnaire (target: >70 "good" threshold)
2. **Task Success Rate**: Percentage of realistic tasks completed successfully
3. **Expert Review**: SQL quality assessment by database administrators

**Comparative Analysis**: Benchmarking against:
- Commercial tools (Tableau Ask Data, Power BI Q&A) on public datasets
- Academic baselines (recent papers' reported metrics on Spider/BIRD)

---

## 8. System Architecture

### 8.1 High-Level Architecture

IDI employs a **modular microservices-inspired architecture** with six specialized components orchestrated by an agent coordinator:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Executive Interface Layer                     │
│         (Web UI: Query Builder + Visualization Dashboard)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ REST API
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                   Multi-Agent Orchestrator                       │
│            (Workflow Router + State Management)                  │
└───┬──────────┬───────────┬───────────┬───────────┬──────────────┘
    │          │           │           │           │
    │          │           │           │           │
┌───▼────┐ ┌──▼──────┐ ┌──▼────────┐ ┌▼────────┐ ┌▼─────────────┐
│Context │ │Query    │ │SQL        │ │Verifi-  │ │Visualization │
│Manager │ │Under-   │ │Generator  │ │cation   │ │Engine        │
│Agent   │ │standing │ │Agent      │ │Agent    │ │              │
│        │ │Agent    │ │           │ │         │ │              │
└────┬───┘ └─────────┘ └───────────┘ └─────────┘ └──────────────┘
     │
     │
┌────▼────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                            │
│  • Vector DB (Context Embeddings)                                │
│  • Relational DB (Target Database + Metadata)                    │
│  • Cache (Query Results + Generated SQL)                         │
└──────────────────────────────────────────────────────────────────┘
```

**Design Principles**:
1. **Separation of Concerns**: Each module handles distinct responsibility
2. **Loose Coupling**: Components communicate via defined interfaces, enabling independent evolution
3. **Fail-Safe Design**: Verification layer prevents execution of malformed queries
4. **Stateful Context**: Session management enables multi-turn conversations

### 8.2 Module Descriptions

#### 8.2.1 Context Manager Agent

**Purpose**: Acquire, store, and retrieve enterprise-specific domain knowledge.

**Responsibilities**:
- Process onboarding survey responses into structured knowledge base
- Embed schema documentation and business glossary using sentence transformers
- Maintain query history for pattern learning
- Retrieve relevant context snippets for query processing via semantic search

**Key Components**:
- Vector database for embedding storage (e.g., Weaviate, ChromaDB)
- Metadata registry for schema information (tables, columns, relationships)
- Context retrieval engine using similarity search

**Inputs**: Survey responses, schema DDL, query logs
**Outputs**: Relevant context snippets for prompt construction

**Technology Candidates**:
- Embedding models: `sentence-transformers/all-mpnet-base-v2` (768-dim embeddings)
- Vector store: ChromaDB (lightweight, embeddable) or FAISS (fast similarity search)
- Metadata: SQLite for simplicity, PostgreSQL for production

#### 8.2.2 Query Understanding Agent

**Purpose**: Parse natural language queries, identify intent, detect ambiguities.

**Responsibilities**:
- Extract query intent (statistics type: average, count, trend, comparison)
- Identify mentioned entities (products, departments, time ranges)
- Detect ambiguities requiring clarification
- Generate structured query representation

**Key Components**:
- Named Entity Recognition (NER) for database entities
- Intent classification (statistical operation detection)
- Ambiguity detection rules (missing parameters, unclear references)
- Clarification question generator

**Inputs**: Raw NL query, keywords selected, context snippets
**Outputs**: Structured intent object + clarification questions (if needed)

**Technology Candidates**:
- Base LLM: Mistral 7B Instruct (efficient, strong instruction-following)
- Alternative: Phi-3 Medium (14B parameters, optimized for reasoning)
- Fine-tuning: LoRA/QLoRA for parameter-efficient adaptation

#### 8.2.3 SQL Generator Agent

**Purpose**: Translate structured query intent into executable SQL.

**Responsibilities**:
- Generate SQL query from intent specification
- Apply schema constraints (foreign keys, data types)
- Incorporate few-shot examples from context
- Handle complex operations (joins, subqueries, aggregations)

**Key Components**:
- Code-specialized LLM for SQL generation
- Prompt template with schema + examples + rules
- Constrained decoding for syntax adherence
- Candidate ranking (if multiple queries generated)

**Inputs**: Structured intent, schema metadata, few-shot examples
**Outputs**: Candidate SQL query (or multiple candidates for ranking)

**Technology Candidates**:
- Primary: Code Llama 13B Instruct (optimized for code generation)
- Alternative: DeepSeek Coder 6.7B (strong SQL performance, smaller footprint)
- Fine-tuning: Supervised fine-tuning on synthetic + benchmark data

#### 8.2.4 Verification Agent

**Purpose**: Validate SQL correctness through three-layer checking.

**Responsibilities**:
- **Layer 1 - Syntax Validation**: Check SQL parses correctly for target dialect
- **Layer 2 - Semantic Verification**: Compare query intent with generated SQL logic
- **Layer 3 - Result Sanity**: Detect anomalous results (negative counts, NULL overload)

**Key Components**:
- SQL parser (e.g., `sqlparse` library)
- Semantic equivalence checker (LLM-based)
- Statistical anomaly detector for results
- Auto-correction engine (regenerate with constraints)

**Inputs**: Generated SQL, original NL query, execution results
**Outputs**: Verification report (pass/fail) + corrected SQL (if errors detected)

**Technology Candidates**:
- Parser: `sqlparse` (Python), `sql-parser` (JavaScript)
- Semantic checker: Same LLM as Query Understanding (Mistral 7B)
- Anomaly detection: Rule-based heuristics + Z-score outlier detection

#### 8.2.5 Visualization Engine

**Purpose**: Automatically select and render appropriate visualizations.

**Responsibilities**:
- Analyze query result structure (dimensionality, data types)
- Select optimal chart type via rule-based heuristics
- Generate interactive visualizations
- Support drill-down and export functionality

**Key Components**:
- Chart type selection engine (decision tree)
- Visualization rendering library
- Statistical overlay generator (trend lines, confidence intervals)

**Inputs**: Query results (tabular), statistical metadata
**Outputs**: Interactive chart specification + rendered visualization

**Technology Candidates**:
- Visualization: Plotly.js (interactive, versatile), Recharts (React-friendly)
- Chart selection rules:
  - Time series (date column + metric) → Line chart
  - Categorical (≤10 categories) + metric → Bar chart
  - Proportion (sum=100%) → Pie/Donut chart
  - Two dimensions + metric → Grouped bar or Heatmap

#### 8.2.6 Multi-Agent Orchestrator

**Purpose**: Coordinate workflow execution and module interactions.

**Responsibilities**:
- Route queries to appropriate modules based on complexity
- Manage conversation state across turns
- Handle error recovery and retries
- Log execution traces for debugging

**Key Components**:
- Workflow engine implementing state machine
- Context aggregator collecting inputs for each stage
- Error handler with retry logic
- Session manager for multi-turn dialogues

**Inputs**: User query, session history, system state
**Outputs**: Orchestrated execution plan + final results

**Technology Candidates**:
- Framework: LangGraph (agent orchestration), AutoGen (multi-agent)
- State management: Python dictionaries + Redis (if persistence needed)
- Workflow: Directed Acyclic Graph (DAG) representation

### 8.3 Data Flow: End-to-End Example

**Scenario**: Executive asks: *"Show me sales performance last quarter"*

**Step-by-Step Flow**:

```
1. User Input → Executive Interface
   Query: "Show me sales performance last quarter"
   Keywords selected: [sales, performance, quarter]

2. Interface → Orchestrator
   Ambiguity detected: "last quarter" undefined

3. Orchestrator → Context Manager
   Retrieves: Fiscal calendar definition, current date

4. Orchestrator → Query Understanding Agent
   Detects: Missing specificity, requires clarification

5. Query Understanding → Interface (via Orchestrator)
   Clarification: "Which quarter? [Q1 2024 | Q2 2024 | Q3 2024 | Q4 2024]"

6. User Selection: "Q3 2024"

7. Orchestrator → Query Understanding Agent (refined)
   Intent: {
     operation: "aggregate",
     metric: "sales_total",
     grouping: "month",
     time_filter: {start: "2024-07-01", end: "2024-09-30"}
   }

8. Orchestrator → Context Manager
   Retrieves: Sales schema, join relationships, few-shot examples

9. Orchestrator → SQL Generator Agent
   Context: Schema + Examples + Intent
   Output:
   SELECT
     DATE_TRUNC('month', order_date) AS month,
     SUM(total_amount) AS sales_total
   FROM orders
   WHERE order_date BETWEEN '2024-07-01' AND '2024-09-30'
   GROUP BY DATE_TRUNC('month', order_date)
   ORDER BY month;

10. Orchestrator → Verification Agent
    Layer 1: Syntax ✓ (valid SQL)
    Layer 2: Semantic ✓ (matches intent)
    Layer 3: (awaits execution)

11. Orchestrator → Database Execution
    Results: [
      {month: "2024-07-01", sales_total: 1500000},
      {month: "2024-08-01", sales_total: 1750000},
      {month: "2024-09-01", sales_total: 1680000}
    ]

12. Verification Agent → Layer 3
    Sanity: ✓ (positive values, reasonable magnitudes)

13. Orchestrator → Visualization Engine
    Analysis: Time series (3 points), single metric
    Selection: Line chart with bar overlay

14. Visualization Engine → Interface
    Renders: Interactive chart showing monthly sales trend
    Additional: KPI card showing Q3 total ($4.93M), QoQ growth (+8%)

15. Interface → User
    Display: Chart + SQL (collapsible) + Export options
```

### 8.4 Key Architectural Decisions

#### Decision 1: Modular vs. End-to-End Monolithic

**Choice**: Modular multi-agent architecture
**Rationale**:
- **Maintainability**: Independent module updates without system-wide redeployment
- **Debugging**: Isolated failure points easier to diagnose
- **Extensibility**: New capabilities (e.g., query optimization) pluggable as modules
- **Performance**: Specialized models (small, focused) vs. single large model

**Trade-off**: Additional orchestration complexity, but acceptable given benefits

#### Decision 2: Local vs. Cloud Deployment

**Choice**: Local-first with optional cloud augmentation
**Rationale**:
- **Cost**: Eliminating per-query API fees for resource-constrained environments
- **Privacy**: Sensitive business data remains on-premises
- **Latency**: No network roundtrip for LLM inference
- **Learning Goal**: Demonstrates optimization techniques for consumer hardware

**Feasibility**: 13B parameter models fit in 8GB VRAM with 4-bit quantization

#### Decision 3: Fine-tuning vs. Prompt Engineering Only

**Choice**: Hybrid approach with fine-tuned specialized models
**Rationale**:
- **Accuracy**: Fine-tuning improves domain-specific performance by 15-25% (Gao et al., 2024)
- **Controllability**: Reduces hallucination and improves instruction adherence
- **Cost-Effectiveness**: Smaller fine-tuned models outperform larger prompted models

**Implementation**: LoRA/QLoRA for parameter-efficient fine-tuning

#### Decision 4: Synchronous vs. Asynchronous Processing

**Choice**: Synchronous pipeline with async option for complex queries
**Rationale**:
- **User Experience**: Immediate feedback for simple queries (<3 seconds)
- **Complexity Handling**: Long-running queries (>10 seconds) handled asynchronously with progress indicators
- **Resource Management**: Prevents concurrent query overload on limited hardware

---

**[Continue to IDI_Project_EN_Part2.md for sections 9-15]**
