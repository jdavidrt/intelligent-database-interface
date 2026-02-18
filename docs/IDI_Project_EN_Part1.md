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

This thesis project proposes the design, development, and evaluation of IDI (Intelligent Database Interface), a comprehensive NL2SQL system tailored for executive decision support. The system integrates seven specialized modules orchestrated through agentic workflows:

1. **Context Manager Agent**: Acquires and maintains enterprise-specific domain knowledge
2. **Query Understanding Agent**: Parses natural language and detects ambiguities
3. **SQL Generator Agent**: Translates structured intent into executable SQL
4. **Verification Agent**: Validates correctness through three-layer checking
5. **Visualization Engine**: Automatically renders statistical insights
6. **Session Manager Agent**: Saves and manages query contexts for investigation continuity
7. **Multi-Agent Orchestrator**: Coordinates dynamic workflow routing

The project emphasizes practical deployment considerations, including resource constraints (local execution on consumer hardware), cost efficiency (minimal cloud dependency), and extensibility (modular architecture enabling component evolution).

**Design Philosophy - Performance Trade-offs**: IDI prioritizes accessibility over raw speed. Complex queries may require up to 30 seconds for processing, deliberately trading rapid response for the ability to execute on resource-constrained devices (standard laptops, workstations). This design choice democratizes access—allowing deployment across organizational tiers without requiring expensive infrastructure. The system provides transparent progress indicators with estimated completion times and user-cancellable operations, ensuring executives understand processing status while maintaining control.

**Conversational Intelligence**: Unlike single-shot query systems, IDI supports iterative investigation workflows where users can ask follow-up questions from results, provide feedback for query refinement, and build upon previous analyses—all within maintained conversational context. Sessions can be saved to preserve entire investigation threads (queries + results + conversation history), enabling users to resume complex analytical paths or share investigative workflows with colleagues.

---

## 2. Problem Statement

### 2.1 Primary Problem

**How can non-technical executives and managers access complex relational databases to extract statistical insights for decision-making without requiring SQL expertise or technical intermediaries, while ensuring query correctness and result interpretability?**

### 2.2 Secondary Problems

1. **Domain Knowledge Gap**: General-purpose LLMs lack enterprise-specific schema understanding, business logic, and domain terminology, leading to incorrect query generation for specialized contexts.

2. **Natural Language Ambiguity**: Executive queries often contain underspecification (missing time ranges, unclear entities), synonymy (multiple terms for same concept), and context-dependence (referencing previous results), complicating semantic parsing.

3. **Schema Complexity**: Enterprise databases feature distributed architectures, nested table structures, multi-dimensional data (arrays within columns), and complex join relationships requiring expert-level SQL knowledge.

4. **Multi-turn Dialogue Limitations**: Exploratory data analysis requires conversational sequences with context preservation, entity tracking, progressive query refinement, and the ability to ask follow-up questions from results or provide feedback for query adjustment—capabilities absent in single-shot NL2SQL systems.

5. **Investigation Continuity**: Complex analytical investigations span multiple sessions and require preserving entire investigative contexts (query sequences, intermediate results, conversational threads) for resumption, sharing, or replication—functionality missing from stateless query systems.

6. **SQL Correctness Verification**: Generated queries may contain semantic errors (wrong aggregations, incorrect joins, missing filters) that produce misleading results, undermining trust and potentially impacting business decisions.

7. **Result Interpretability**: Raw tabular outputs lack visual context for trend identification, comparative analysis, and pattern recognition—requiring automatic visualization selection and rendering.

8. **Computational Resource Constraints**: State-of-the-art LLMs (70B+ parameters) demand extensive GPU resources and cloud API costs, creating barriers for resource-constrained environments. Additionally, complex queries may require extended processing times (up to 30 seconds), necessitating transparent progress communication and user control mechanisms (cancellation, status updates).

### 2.3 Research Questions

1. Can a structured context acquisition process (surveys, schema documentation) provide sufficient domain knowledge for accurate NL2SQL in specialized business contexts?

2. Does keyword-guided query construction combined with clarification dialogues effectively resolve natural language ambiguity compared to free-form input?

3. What verification mechanisms are necessary and sufficient to achieve >90% SQL correctness in enterprise scenarios?

4. How can multi-agent architectures improve NL2SQL robustness compared to monolithic end-to-end models?

5. What is the optimal balance between model size, accuracy, and inference latency for local deployment on consumer hardware (16GB RAM, 8GB VRAM)?

6. How does session-based investigation continuity (saving queries, results, and conversational context) impact analytical workflow effectiveness compared to stateless query systems?

7. What progress communication mechanisms (estimated completion times, processing status updates, cancellation controls) are necessary to maintain user trust during extended query processing (up to 30 seconds)?

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

**Design, develop, and evaluate IDI (Intelligent Database Interface), a modular multi-agent NL2SQL system that enables non-technical executives to extract statistical insights from relational databases through conversational natural language queries with contextual awareness, ambiguity resolution, automated verification, and session-based investigation continuity, achieving >90% query correctness while operating on local consumer hardware with transparent progress communication for extended processing times (up to 30 seconds).**

### 6.2 Specific Objectives

#### Specific Objective 1: Requirements Analysis

**Conduct comprehensive requirements analysis for an executive-focused NL2SQL system, identifying functional and non-functional requirements, success criteria, and evaluation metrics through literature review, competitive analysis, and stakeholder need assessment.**

**Expected Outcomes**:
- Requirements specification document detailing functional modules, user personas, and use cases
- Benchmark dataset selection justification (Spider, BIRD, or domain-specific alternatives)
- Success metrics definition (accuracy thresholds, latency limits, usability scores)

#### Specific Objective 2: System Design

**Design the IDI modular architecture, specifying component responsibilities, inter-agent communication protocols, data flows, session management mechanisms, progress communication strategies, and technology stack selection optimized for local deployment on consumer hardware (16GB RAM, 8GB VRAM) with extended query timeouts (up to 30 seconds).**

**Expected Outcomes**:
- System architecture diagrams (component, deployment, sequence diagrams) including Session Manager module
- Module interface specifications (inputs, outputs, APIs) with multi-turn conversation flows
- Technology stack justification document comparing alternatives (LLM choices, frameworks, databases)
- Context acquisition survey design and metadata schema
- Session persistence schema (queries, results, conversation history, metadata)
- Progress indicator design (estimated times, processing phases, cancellation mechanisms)

#### Specific Objective 3: Solution Development

**Implement the seven core IDI modules (Context Manager, Query Understanding, SQL Generator, Verification Agent, Visualization Engine, Session Manager, Multi-Agent Orchestrator) with synthetic training data generation, model fine-tuning pipelines, conversational flow management, and user interface components including progress indicators and session controls.**

**Expected Outcomes**:
- Functional prototype system with web-based interface supporting multi-turn conversations
- Fine-tuned LLM models for NL understanding and SQL generation
- Synthetic training dataset (minimum 500 query-SQL pairs)
- Session management implementation (save, load, list, delete, export functionality)
- Progress indicator system with estimated completion times and cancellation capability
- Test suite with unit, integration, and system-level tests including multi-turn conversation scenarios

#### Specific Objective 4: Results Analysis

**Evaluate IDI performance through quantitative benchmarking (execution accuracy, latency, verification effectiveness, session usage patterns) and qualitative assessment (user study with multi-turn tasks, expert review, progress indicator effectiveness), comparing results against baseline methods and identifying improvement opportunities.**

**Expected Outcomes**:
- Performance evaluation report with statistical significance testing including query timeout analysis
- User study results (task success rate, System Usability Scale scores, multi-turn conversation effectiveness)
- Session feature evaluation (usage frequency, resumption patterns, sharing behavior)
- Progress indicator assessment (user satisfaction during extended processing, cancellation usage)
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

IDI employs a **modular microservices-inspired architecture** with seven specialized components orchestrated by an agent coordinator:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Executive Interface Layer                     │
│  (Web UI: Query Builder + Visualization Dashboard +              │
│   Progress Indicators + Session Controls)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ REST API
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                   Multi-Agent Orchestrator                       │
│     (Workflow Router + State Management + Progress Tracker)      │
└───┬──────────┬───────────┬───────────┬───────────┬─────────┬───┘
    │          │           │           │           │         │
    │          │           │           │           │         │
┌───▼────┐ ┌──▼──────┐ ┌──▼────────┐ ┌▼────────┐ ┌▼──────┐ ┌▼────────┐
│Context │ │Query    │ │SQL        │ │Verifi-  │ │Visual- │ │Session  │
│Manager │ │Under-   │ │Generator  │ │cation   │ │ization │ │Manager  │
│Agent   │ │standing │ │Agent      │ │Agent    │ │Engine  │ │Agent    │
│        │ │Agent    │ │           │ │         │ │        │ │         │
└────┬───┘ └─────────┘ └───────────┘ └─────────┘ └────────┘ └────┬────┘
     │                                                              │
     │                                                              │
┌────▼──────────────────────────────────────────────────────────┬─▼───┐
│                    Data Storage Layer                          │     │
│  • Vector DB (Context Embeddings)                              │     │
│  • Relational DB (Target Database + Metadata)                  │     │
│  • Cache (Query Results + Generated SQL)                       │Sess-│
│  • Session Store (Queries + Results + Conversation History +   │ion  │
│                   Metadata: names, tags, timestamps)           │Store│
└────────────────────────────────────────────────────────────────┴─────┘
```

**Design Principles**:
1. **Separation of Concerns**: Each module handles distinct responsibility
2. **Loose Coupling**: Components communicate via defined interfaces, enabling independent evolution
3. **Fail-Safe Design**: Verification layer prevents execution of malformed queries
4. **Stateful Context**: Session management enables multi-turn conversations and investigation continuity
5. **User-Controlled Processing**: Transparent progress communication and cancellation capability for extended queries (up to 30 seconds)
6. **Investigation Persistence**: Full session context preservation (queries, results, conversation threads) for resumption and sharing

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
- Manage conversation state within active session
- Handle error recovery and retries
- Track query processing progress and estimated completion times
- Manage query cancellation requests
- Log execution traces for debugging

**Key Components**:
- Workflow engine implementing state machine
- Context aggregator collecting inputs for each stage
- Error handler with retry logic
- Progress tracker with timeout management (up to 30 seconds)
- Cancellation handler for user-initiated query termination

**Inputs**: User query, session history, system state
**Outputs**: Orchestrated execution plan + final results

**Technology Candidates**:
- Framework: LangGraph (agent orchestration), AutoGen (multi-agent)
- State management: Python dictionaries + Redis (if persistence needed)
- Workflow: Directed Acyclic Graph (DAG) representation

#### 8.2.7 Session Manager Agent

**Purpose**: Persist and manage investigative sessions for continuity and sharing.

**Responsibilities**:
- Save complete session contexts (queries, results, conversation history)
- Manage session metadata (names, descriptions, tags, timestamps)
- List, search, and filter saved sessions
- Load and resume previous sessions with full context restoration
- Delete and archive sessions
- Export sessions for sharing or backup
- Track session usage analytics

**Key Components**:
- Session persistence layer (database storage)
- Metadata indexing for fast search/retrieval
- Conversation history serializer/deserializer
- Results snapshot manager (handling large datasets)
- Export formatter (JSON, CSV, or shareable formats)
- Session lifecycle manager (creation, update, deletion)

**Inputs**:
- Save request: Current query, results, conversation history, user-provided metadata
- Load request: Session ID or search criteria
- Management operations: List, delete, export commands

**Outputs**:
- Saved session confirmation with session ID
- Loaded session context (full conversation state + results)
- Session list with metadata
- Exported session files

**Technology Candidates**:
- Storage: PostgreSQL (relational metadata + JSONB for flexible storage) or MongoDB (document-oriented)
- Serialization: JSON for conversation history, Parquet/CSV for large result sets
- Metadata schema:
  ```
  Session {
    id: UUID
    name: String (user-provided)
    description: String (optional)
    tags: String[] (user-provided)
    created_at: Timestamp
    updated_at: Timestamp
    queries: Query[] (chronological order)
    conversation_history: Message[] (full context)
    results_snapshots: Result[] (query outputs)
  }
  ```
- Search: Full-text search on names/descriptions/tags using PostgreSQL FTS or Elasticsearch

### 8.3 Data Flow: Multi-Turn Conversation Example

**Scenario**: Executive conducts an iterative sales investigation with follow-up questions, feedback, and session saving.

**Step-by-Step Flow**:

```
═══════════════════════════════════════════════════════════════
TURN 1: Initial Query
═══════════════════════════════════════════════════════════════

1. User Input → Executive Interface
   Query: "Show me sales performance last quarter"
   Keywords selected: [sales, performance, quarter]

2. Interface → Orchestrator
   Status: "Analyzing your question..."
   Ambiguity detected: "last quarter" undefined

3. Orchestrator → Context Manager
   Retrieves: Fiscal calendar definition, current date

4. Orchestrator → Query Understanding Agent
   Detects: Missing specificity, requires clarification

5. Query Understanding → Interface (via Orchestrator)
   Clarification: "Which quarter? [Q1 2024 | Q2 2024 | Q3 2024 | Q4 2024]"

6. User Selection: "Q3 2024"

7. Orchestrator → Query Understanding Agent (refined)
   Status: "Understanding your request..."
   Intent: {
     operation: "aggregate",
     metric: "sales_total",
     grouping: "month",
     time_filter: {start: "2024-07-01", end: "2024-09-30"}
   }

8. Orchestrator → Context Manager
   Status: "Gathering relevant database information..."
   Retrieves: Sales schema, join relationships, few-shot examples

9. Orchestrator → SQL Generator Agent
   Status: "Crafting your query... (Estimated: 8 seconds)"
   Progress: [████████░░░░] 60% - "Constructing SQL logic..."
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
    Status: "Verifying query correctness..."
    Layer 1: Syntax ✓ (valid SQL)
    Layer 2: Semantic ✓ (matches intent)
    Layer 3: (awaits execution)

11. Orchestrator → Database Execution
    Status: "Executing query and retrieving results..."
    Results: [
      {month: "2024-07-01", sales_total: 1500000},
      {month: "2024-08-01", sales_total: 1750000},
      {month: "2024-09-01", sales_total: 1680000}
    ]

12. Verification Agent → Layer 3
    Sanity: ✓ (positive values, reasonable magnitudes)

13. Orchestrator → Visualization Engine
    Status: "Creating visualization..."
    Analysis: Time series (3 points), single metric
    Selection: Line chart with bar overlay

14. Visualization Engine → Interface
    Renders: Interactive chart showing monthly sales trend
    Additional: KPI card showing Q3 total ($4.93M), QoQ growth (+8%)

15. Interface → User
    Display: Chart + SQL (collapsible) + Export options
    Status: ✓ Complete (Total time: 7.2 seconds)
    Options: [Ask Follow-up] [Give Feedback] [Save to Session]

═══════════════════════════════════════════════════════════════
TURN 2: Follow-up Question from Results
═══════════════════════════════════════════════════════════════

16. User Input → Executive Interface
    Follow-up Query: "Which region drove the August peak?"
    Context: Previous query + results maintained

17. Orchestrator → Query Understanding Agent
    Status: "Analyzing follow-up question..."
    Context-aware parsing: References August from previous result
    Intent: {
      operation: "breakdown",
      metric: "sales_total",
      grouping: "region",
      time_filter: {start: "2024-08-01", end: "2024-08-31"}
    }

18. Orchestrator → SQL Generator Agent
    Status: "Building regional breakdown query... (Estimated: 12 seconds)"
    Progress: [██████░░░░░░] 50% - "Analyzing multi-table relationships..."
    Output:
    SELECT
      r.region_name,
      SUM(o.total_amount) AS sales_total
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN regions r ON c.region_id = r.region_id
    WHERE o.order_date BETWEEN '2024-08-01' AND '2024-08-31'
    GROUP BY r.region_name
    ORDER BY sales_total DESC;

19. [Verification + Execution + Visualization pipeline...]
    Status: "Verifying and executing..."
    Results: [
      {region_name: "Northeast", sales_total: 780000},
      {region_name: "West", sales_total: 520000},
      {region_name: "South", sales_total: 450000}
    ]

20. Interface → User
    Display: Bar chart showing regional breakdown
    Insight: "Northeast contributed 44.6% of August sales"
    Status: ✓ Complete (Total time: 11.8 seconds)

═══════════════════════════════════════════════════════════════
TURN 3: User Feedback for Refinement
═══════════════════════════════════════════════════════════════

21. User Input → Executive Interface
    Feedback: "Show me just the top 3 regions and include product categories"
    Context: Previous query refined based on user preference

22. Orchestrator → Query Understanding Agent
    Status: "Refining query based on feedback..."
    Intent: {
      operation: "breakdown",
      metric: "sales_total",
      grouping: ["region", "product_category"],
      limit: 3,
      time_filter: {start: "2024-08-01", end: "2024-08-31"}
    }

23. Orchestrator → SQL Generator Agent
    Status: "Building multi-dimensional breakdown... (Estimated: 18 seconds)"
    Progress: [████░░░░░░░░] 30% - "Optimizing join strategy..."
    Progress: [████████░░░░] 65% - "Constructing aggregation logic..."
    [User can click [Cancel] button at any time]

24. [Verification + Execution + Visualization...]
    Results: Grouped bar chart showing categories per top 3 regions
    Status: ✓ Complete (Total time: 17.3 seconds)

═══════════════════════════════════════════════════════════════
TURN 4: Session Saving
═══════════════════════════════════════════════════════════════

25. User Action → Session Manager
    Clicks "Save to Session"

26. Interface → Session Manager Agent
    Prompt for metadata:
      - Session Name: [User enters: "Q3 2024 Sales Regional Analysis"]
      - Description: [Optional: "Investigating August peak performance"]
      - Tags: [User enters: "sales, Q3, regional, 2024"]

27. Session Manager → Storage Layer
    Saves:
      - All 3 queries (original + 2 follow-ups)
      - All result sets
      - Complete conversation history with clarifications
      - Metadata: {
          session_id: "550e8400-e29b-41d4-a716-446655440000",
          created_at: "2024-11-18T14:32:00Z",
          name: "Q3 2024 Sales Regional Analysis",
          tags: ["sales", "Q3", "regional", "2024"]
        }

28. Session Manager → Interface
    Confirmation: "✓ Session saved successfully!"
    Options: [Share Session] [Export as PDF] [Continue Investigation]

29. User can later:
    - Resume session from Session Library
    - Load complete context (queries + results + conversation)
    - Share with colleagues for collaborative analysis
    - Export investigation thread for reporting
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

#### Decision 4: Extended Query Timeout (30 seconds) with Progress Communication

**Choice**: Accept processing times up to 30 seconds with transparent progress indicators and user cancellation
**Rationale**:
- **Accessibility over Speed**: Prioritizes deployment on resource-constrained devices (consumer laptops, standard workstations) over raw performance, democratizing access across organizational tiers
- **Complex Query Support**: Enterprise-grade multi-table joins, aggregations, and verification pipelines require computational headroom unavailable in sub-second constraints
- **User Trust Maintenance**: Transparent progress communication (estimated completion times, processing phase descriptions, visual progress bars) maintains engagement during extended processing
- **User Control**: Cancellation capability empowers users to abort non-productive queries, preventing frustration and resource waste

**Implementation**:
- **Timeout Tiers**: Simple queries (3-5s), moderate complexity (8-15s), complex multi-join/verification (20-30s)
- **Progress Phases**: Display creative, informative status messages:
  - "Analyzing your question..."
  - "Gathering relevant database information..."
  - "Crafting your query... (Estimated: 12 seconds)"
  - "Constructing SQL logic..." [████████░░░░] 60%
  - "Verifying query correctness..."
  - "Executing and retrieving results..."
- **Cancellation Protocol**: User-initiated abortion triggers graceful shutdown (LLM inference termination, resource cleanup, partial results return if available)
- **Adaptive Estimation**: Machine learning model predicts completion time based on query complexity, schema size, and historical performance

**Trade-off**: Longer wait times vs. broader deployment feasibility—acceptable for analytical use cases where insight quality supersedes response latency

#### Decision 5: Session-Based vs. Stateless Query System

**Choice**: Persistent session management with full context preservation
**Rationale**:
- **Investigation Continuity**: Complex analytical tasks span multiple queries over hours/days—session persistence enables resumption without context loss
- **Knowledge Sharing**: Exportable sessions facilitate collaborative analysis and onboarding (senior analysts share investigation paths with junior colleagues)
- **Pattern Replication**: Saved sessions become reusable templates for recurring analyses (monthly sales reviews, quarterly compliance audits)
- **Accountability**: Audit trail of queries and results supports regulatory compliance and decision traceability

**Implementation**:
- **Session Scope**: Queries, results, conversation history, clarifications, visualizations
- **Metadata**: User-provided names, descriptions, tags; system-generated timestamps, usage statistics
- **Storage**: Relational database (PostgreSQL JSONB) for structured metadata + document store for large result sets
- **Operations**: Save, load, list, search (full-text on metadata), delete, export (JSON/PDF formats)
- **User Experience**: Manual save (user-initiated "Save to Session" button) to avoid cluttering storage with exploratory dead-ends

**Trade-off**: Additional storage overhead and complexity vs. significantly enhanced usability for iterative workflows

---

**[Continue to IDI_Project_EN_Part2.md for sections 9-15]**
