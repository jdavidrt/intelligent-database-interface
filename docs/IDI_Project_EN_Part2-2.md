
## 10. Technology Stack Analysis

### 10.1 Backend Technologies

#### 10.1.1 Programming Language: Python 3.11+

**Justification**:
- **Ecosystem**: Richest ML/NLP library ecosystem (Transformers, LangChain, SQLAlchemy)
- **Productivity**: Rapid prototyping with dynamic typing, expressive syntax
- **Community**: Extensive documentation and Stack Overflow support
- **Integration**: Seamless integration with LLM inference libraries

**Alternatives Considered**:
- **JavaScript/TypeScript**: Weaker ML ecosystem, better for full-stack if unified language desired
- **Java**: More verbose, slower development, but stronger enterprise adoption

**Decision**: Python for backend services, with potential TypeScript migration for production if needed.

#### 10.1.2 LLM Inference Framework

**Primary Choice: Hugging Face Transformers + bitsandbytes**

**Justification**:
- **Model Support**: Access to 100K+ pre-trained models via Hub
- **Quantization**: Seamless 4-bit quantization via bitsandbytes integration
- **Flexibility**: Easy swapping between models for experimentation
- **Documentation**: Industry-standard with comprehensive guides

```python
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

tokenizer = AutoTokenizer.from_pretrained("codellama/CodeLlama-13b-Instruct-hf")
model = AutoModelForCausalLM.from_pretrained(
    "codellama/CodeLlama-13b-Instruct-hf",
    load_in_4bit=True,
    device_map="auto"
)

sql_generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512
)
```

**Alternatives**:
- **LangChain**: Higher-level abstractions for agent workflows (use as complement, not replacement)
- **vLLM**: Optimized inference server (overkill for single-user local deployment)
- **llama.cpp**: CPU-optimized C++ implementation (consider if GPU insufficient)

#### 10.1.3 Agent Orchestration Framework

**Primary Choice: LangGraph**

**Justification**:
- **State Management**: Built-in conversation state tracking
- **Workflow Definition**: DAG-based agent coordination with conditional routing
- **LLM Integration**: Native Hugging Face and OpenAI compatibility
- **Debugging**: Graph visualization for workflow inspection

```python
from langgraph.graph import Graph, END

workflow = Graph()

workflow.add_node("understand_query", query_understanding_agent)
workflow.add_node("clarify", clarification_dialogue)
workflow.add_node("generate_sql", sql_generator_agent)
workflow.add_node("verify", verification_agent)
workflow.add_node("visualize", visualization_engine)

workflow.add_conditional_edges(
    "understand_query",
    route_based_on_ambiguity,
    {
        "clear": "generate_sql",
        "ambiguous": "clarify"
    }
)

workflow.add_edge("clarify", "generate_sql")
workflow.add_edge("generate_sql", "verify")
workflow.add_conditional_edges(
    "verify",
    route_based_on_verification,
    {
        "pass": "visualize",
        "fail": "generate_sql",  # Retry
        "critical_error": END
    }
)
workflow.add_edge("visualize", END)

workflow.set_entry_point("understand_query")
app = workflow.compile()
```

**Alternatives**:
- **AutoGen**: Microsoft's multi-agent framework (more complex, overkill for this scope)
- **Custom Implementation**: Full control but high development overhead

#### 10.1.4 Vector Database

**Primary Choice: ChromaDB**

**Justification**:
- **Embeddable**: Runs in-process, no separate server (simplicity for local deployment)
- **Performance**: Fast similarity search for context retrieval (<50ms for 10K embeddings)
- **Ease of Use**: Pythonic API with minimal configuration
- **Cost**: Free and open-source

```python
import chromadb
from sentence_transformers import SentenceTransformer

chroma_client = chromadb.Client()
context_collection = chroma_client.create_collection("domain_context")

# Embed and store context
embedding_model = SentenceTransformer('all-mpnet-base-v2')
context_texts = [...]  # From survey responses
embeddings = embedding_model.encode(context_texts)

context_collection.add(
    embeddings=embeddings.tolist(),
    documents=context_texts,
    ids=[f"ctx_{i}" for i in range(len(context_texts))]
)

# Retrieve relevant context
query_embedding = embedding_model.encode(["user query"])
results = context_collection.query(
    query_embeddings=query_embedding.tolist(),
    n_results=3
)
```

**Alternatives**:
- **FAISS**: Faster for large-scale (>1M vectors), but requires more setup
- **Weaviate**: Feature-rich but overkill (requires Docker, more complex)
- **Pinecone**: Cloud-hosted (avoids local requirement, incurs costs)

#### 10.1.5 Relational Database

**Development: SQLite**
- **Rationale**: Zero-configuration, file-based, perfect for prototyping

**Production Recommendation: PostgreSQL**
- **Rationale**: Enterprise-grade, best SQL standard compliance, JSON support, extensive extensions

```python
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

# Development
engine = create_engine('sqlite:///idi_dev.db')

# Production
engine = create_engine('postgresql://user:password@localhost:5432/idi_prod')

Session = sessionmaker(bind=engine)
session = Session()

# Metadata for schema inspection
metadata = MetaData()
metadata.reflect(bind=engine)
tables = metadata.tables.keys()  # Get all table names
```

**Alternatives**:
- **MySQL**: Widely used but weaker SQL standard adherence
- **SQL Server**: Strong choice for Windows environments, but licensing costs

#### 10.1.6 Fine-Tuning Library

**Primary Choice: PEFT (Parameter-Efficient Fine-Tuning)**

**Justification**:
- **Memory Efficiency**: QLoRA enables 13B model fine-tuning on 8GB VRAM
- **Speed**: 3-4x faster training than full fine-tuning
- **Quality**: Minimal accuracy degradation vs. full fine-tuning (<1-2%)

```python
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import TrainingArguments, Trainer

# Prepare base model for QLoRA
model = prepare_model_for_kbit_training(base_model)

# Configure LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none"
)

model = get_peft_model(model, lora_config)

# Training
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset
)

trainer.train()
```

**Alternatives**:
- **Full Fine-Tuning**: Requires 4x more memory, minimal benefit
- **Adapter Layers**: Similar concept, but PEFT more actively maintained

#### 10.1.7 Session Storage and Management

**Primary Choice: PostgreSQL with JSONB**

**Justification**:
- **Flexible Schema**: JSONB columns store conversation history and results with full indexing
- **Full-Text Search**: Built-in FTS for searching session names/descriptions/tags
- **ACID Compliance**: Ensures session data integrity
- **Array Support**: Native PostgreSQL arrays for tags
- **Performance**: GIN indexes enable fast search on JSONB and text arrays

```python
from sqlalchemy import create_engine, Column, String, ARRAY, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid

Base = declarative_base()

class Session(Base):
    __tablename__ = 'sessions'

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    tags = Column(ARRAY(String))  # PostgreSQL array for tags
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    data = Column(JSONB, nullable=False)  # Stores queries, conversation, results

# Create engine
engine = create_engine('postgresql://user:password@localhost:5432/idi_sessions')

# Create all tables
Base.metadata.create_all(engine)

# Session maker
Session = sessionmaker(bind=engine)
db_session = Session()
```

**Schema Migration** (using Alembic):
```python
# alembic/versions/001_create_sessions.py
def upgrade():
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('tags', postgresql.ARRAY(sa.String)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('data', postgresql.JSONB, nullable=False)
    )

    # Create indexes
    op.create_index(
        'sessions_search_idx',
        'sessions',
        [sa.text("to_tsvector('english', name || ' ' || description || ' ' || array_to_string(tags, ' '))")],
        postgresql_using='gin'
    )
    op.create_index('sessions_tags_idx', 'sessions', ['tags'], postgresql_using='gin')
    op.create_index('sessions_created_idx', 'sessions', ['created_at'], postgresql_ops={'created_at': 'DESC'})
```

**Query Examples**:

```python
# Save session
new_session = Session(
    session_id=uuid.uuid4(),
    name="Q3 2024 Sales Regional Analysis",
    description="Investigating August peak performance",
    tags=["sales", "Q3", "regional", "2024"],
    data={
        "queries": [...],
        "conversation": [...],
        "results": [...]
    }
)
db_session.add(new_session)
db_session.commit()

# Full-text search
search_results = db_session.query(Session).filter(
    sa.text("to_tsvector('english', name || ' ' || description) @@ plainto_tsquery('sales peak')")
).all()

# Filter by tags
tagged_sessions = db_session.query(Session).filter(
    Session.tags.contains(['sales', 'Q3'])
).all()

# Get recent sessions
recent = db_session.query(Session).order_by(Session.updated_at.desc()).limit(10).all()
```

**Alternatives**:
- **MongoDB**: Document-oriented, natural fit for JSON data, but weaker for relational queries
- **Redis with JSON**: Fast but limited query capabilities, better suited for caching
- **SQLite with JSON1 extension**: Good for development, lacks full-text search and array support

#### 10.1.8 Real-Time Communication: WebSockets

**Primary Choice: FastAPI WebSockets + Socket.IO (optional)**

**Justification**:
- **Progress Updates**: Real-time progress indicators during query processing
- **Cancellation**: User can abort queries mid-execution
- **Low Latency**: <100ms update frequency for smooth progress bars
- **Built-in**: FastAPI has native WebSocket support

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio

app = FastAPI()

# Track active connections
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/query/{session_id}")
async def query_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket

    try:
        while True:
            # Receive query from client
            data = await websocket.receive_json()

            if data["type"] == "query":
                # Process query with progress updates
                async for progress in process_query_with_progress(data["query"], session_id):
                    await websocket.send_json({
                        "type": "progress",
                        "phase": progress.phase,
                        "percent": progress.percent,
                        "message": progress.message,
                        "estimated_remaining": progress.estimated_remaining
                    })

                # Send final results
                await websocket.send_json({
                    "type": "result",
                    "data": progress.final_result
                })

            elif data["type"] == "cancel":
                # Handle cancellation
                cancel_query(session_id)
                await websocket.send_json({
                    "type": "cancelled",
                    "message": "Query cancelled by user"
                })

    except WebSocketDisconnect:
        del active_connections[session_id]

async def send_progress_update(session_id: str, progress: ProgressUpdate):
    """Send progress update to specific client."""
    if session_id in active_connections:
        await active_connections[session_id].send_json({
            "type": "progress",
            "data": progress.dict()
        })
```

**Frontend (React + WebSocket)**:
```typescript
function useQueryWebSocket(sessionId: string) {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(`ws://localhost:8000/ws/query/${sessionId}`);

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'progress') {
        setProgress(message.data);
      } else if (message.type === 'result') {
        setResult(message.data);
        setProgress(null);
      }
    };

    return () => ws.current?.close();
  }, [sessionId]);

  const cancelQuery = () => {
    ws.current?.send(JSON.stringify({ type: 'cancel' }));
  };

  return { progress, result, cancelQuery };
}
```

**Alternatives**:
- **Server-Sent Events (SSE)**: One-way communication, simpler but can't cancel
- **Polling**: Simple but inefficient, high latency
- **Socket.IO**: More features but heavier, overkill for this use case

### 10.2 Frontend Technologies

#### 10.2.1 Framework: React.js with TypeScript

**Justification**:
- **Component Reusability**: Modular UI components for query builder, visualizations
- **Ecosystem**: Rich library ecosystem for charts (Recharts, Plotly)
- **Type Safety**: TypeScript prevents runtime errors, improves maintainability
- **Developer Experience**: Hot reload, extensive tooling (VS Code)

**Alternatives**:
- **Vue.js**: Easier learning curve, but smaller ecosystem
- **Svelte**: Better performance, but less mature tooling
- **Plain HTML/JS**: Faster initial development, but scales poorly

#### 10.2.2 UI Component Library: shadcn/ui

**Justification**:
- **Customization**: Copy-paste components, full control over styling
- **Accessibility**: ARIA-compliant components out of box
- **Modern Design**: Tailwind-based, responsive by default
- **No Dependency Bloat**: Only include components you use

**Alternatives**:
- **Material-UI**: Feature-rich but heavy bundle size
- **Ant Design**: Great for enterprise, but opinionated styling
- **Chakra UI**: Good balance, but less flexible than shadcn

#### 10.2.3 Visualization Library: Recharts

**Justification**:
- **React Integration**: Declarative API, native React components
- **Customization**: Full control over chart appearance
- **Responsiveness**: Automatic responsive sizing
- **Interactivity**: Built-in tooltips, legends, click handlers

```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface SalesData {
  month: string;
  revenue: number;
}

const SalesChart: React.FC<{ data: SalesData[] }> = ({ data }) => (
  <LineChart width={600} height={300} data={data}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="month" />
    <YAxis />
    <Tooltip />
    <Legend />
    <Line type="monotone" dataKey="revenue" stroke="#8884d8" activeDot={{ r: 8 }} />
  </LineChart>
);
```

**Alternatives**:
- **Plotly.js**: More chart types, but heavier bundle
- **D3.js**: Maximum flexibility, but steep learning curve
- **Chart.js**: Simpler API, but less React-friendly

#### 10.2.4 State Management: Zustand

**Justification**:
- **Simplicity**: Minimal boilerplate vs. Redux
- **Performance**: React 18 concurrent mode compatible
- **TypeScript Support**: Excellent type inference

```typescript
import create from 'zustand';

interface ConversationState {
  messages: Message[];
  currentQuery: string;
  results: QueryResult | null;
  addMessage: (message: Message) => void;
  setResults: (results: QueryResult) => void;
}

const useConversationStore = create<ConversationState>((set) => ({
  messages: [],
  currentQuery: '',
  results: null,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setResults: (results) => set({ results })
}));
```

**Alternatives**:
- **Redux**: More structure, but excessive for this scope
- **Context API**: Built-in, but performance concerns for frequent updates
- **Jotai**: Atomic state management, interesting alternative

### 10.3 Infrastructure & Deployment

#### 10.3.1 Containerization: Docker

**Justification**:
- **Reproducibility**: Consistent environment across development and deployment
- **Dependency Isolation**: Avoid "works on my machine" issues
- **Deployment Simplicity**: Single container deployment to any host

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
    environment:
      - MODEL_PATH=/app/models
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

#### 10.3.2 API Framework: FastAPI

**Justification**:
- **Performance**: Async support, ~2-3x faster than Flask
- **Type Safety**: Pydantic models for request/response validation
- **Documentation**: Auto-generated OpenAPI/Swagger docs
- **WebSockets**: Native support for real-time updates

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="IDI API", version="1.0.0")

class QueryRequest(BaseModel):
    query: str
    session_id: str
    keywords: List[str] = []

class QueryResponse(BaseModel):
    sql: str
    results: List[Dict[str, Any]]
    visualization: ChartSpec
    confidence: float

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # Orchestrate agents
        result = await orchestrator.process(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Alternatives**:
- **Flask**: Simpler, but no async support
- **Django**: Full-stack framework, overkill for API-only backend

#### 10.3.3 Version Control: Git + GitHub

**Repository Structure**:
```
idi-project/
├── backend/
│   ├── agents/
│   ├── models/
│   ├── utils/
│   └── tests/
├── frontend/
│   ├── src/
│   └── tests/
├── data/
│   ├── benchmarks/
│   └── synthetic/
├── docs/
├── docker-compose.yml
└── README.md
```

**CI/CD**: GitHub Actions for automated testing

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/
```

### 10.4 Development Tools

**IDE**: Visual Studio Code
- **Extensions**: Python, Pylance, Jupyter, Docker, GitLens

**Testing**:
- **Unit Tests**: pytest (Python), Jest (TypeScript)
- **Integration Tests**: TestContainers for database testing
- **Load Testing**: Locust for API performance testing

**Code Quality**:
- **Linting**: ruff (Python), ESLint (TypeScript)
- **Formatting**: black (Python), Prettier (TypeScript)
- **Type Checking**: mypy (Python), TypeScript compiler

---

## 11. Implementation Plan

### 11.1 Overview

**Duration**: 16 weeks  
**Structure**: 4 phases aligned with specific objectives  
**Workload**: ~20-25 hours/week (realistic for thesis project)

### 11.2 Phase 1: Requirements Analysis (Weeks 1-4)

**Aligned with Specific Objective 1**

#### Activity 1.1: Literature Review and Competitive Analysis (Week 1-2)

**Tasks**:
- Deep dive into recent NL2SQL papers (Luo et al., Li et al., Kumar et al.)
- Analyze commercial solutions (Tableau Ask Data, Power BI Q&A, AWS Athena NL)
- Document strengths, weaknesses, and gaps

**Deliverables**:
- State-of-the-art summary document (10-15 pages)
- Competitive feature matrix comparing 5+ existing solutions
- Gap analysis identifying IDI's unique contributions

**Success Criteria**:
- Identified at least 3 unaddressed challenges in existing work
- Documented at least 5 potential architectural design decisions

#### Activity 1.2: Benchmark Dataset Selection and Analysis (Week 2-3)

**Tasks**:
- Download and analyze Spider, BIRD, and domain-specific benchmarks
- Evaluate dataset characteristics (size, complexity, domain diversity)
- Select primary and secondary benchmarks for evaluation
- Create custom test cases for executive-specific queries

**Deliverables**:
- Benchmark selection justification document
- Custom executive query test set (50-100 queries)
- Baseline performance documentation (existing solutions on selected benchmarks)

**Success Criteria**:
- Selected benchmarks cover target difficulty levels (multi-table joins, aggregations)
- Custom queries represent realistic executive information needs

#### Activity 1.3: Requirements Specification and Metrics Definition (Week 3-4)

**Tasks**:
- Define functional requirements (per module)
- Define non-functional requirements (performance, usability, scalability)
- Specify success metrics with quantitative thresholds
- Create user personas and use case scenarios

**Deliverables**:
- Software Requirements Specification (SRS) document (15-20 pages)
- Evaluation metrics definition with target thresholds
- 5+ detailed use case scenarios with expected system behavior

**Success Criteria**:
- All 7 modules have specified inputs, outputs, and responsibilities (including Session Manager)
- Metrics defined for accuracy (>90%), latency (<30s for complex queries), usability (SUS >70)
- Session management requirements specified (save, load, search, export)

**Phase 1 Milestone**: Requirements document approved, benchmarks prepared, clear success criteria established.

---

### 11.3 Phase 2: System Design (Weeks 5-8)

**Aligned with Specific Objective 2**

#### Activity 2.1: Architecture Design and Module Specification (Week 5-6)

**Tasks**:
- Design high-level system architecture (component diagram)
- Specify module interfaces (API contracts)
- Design data flows between components (sequence diagrams)
- Document design patterns and architectural decisions

**Deliverables**:
- System architecture document with diagrams (UML component, deployment)
- Module interface specifications (input/output schemas for each agent)
- Sequence diagrams for 3+ key workflows (query processing, clarification, error handling)
- Architecture Decision Records (ADRs) for major choices

**Success Criteria**:
- Clear separation of concerns with minimal coupling between modules
- All interfaces specified with type signatures
- Diagrams reviewed and validated for logical consistency

#### Activity 2.2: Technology Stack Selection and Justification (Week 6-7)

**Tasks**:
- Evaluate LLM candidates (benchmark on sample queries)
- Compare framework options (LangChain vs. LangGraph vs. custom)
- Test quantization impact on accuracy (4-bit vs. 8-bit vs. FP16)
- Prototype inference on target hardware (measure VRAM usage, latency)

**Deliverables**:
- Technology stack justification document (5-10 pages)
- Preliminary performance benchmarks (3+ model candidates tested)
- Quantization trade-off analysis (accuracy vs. memory vs. speed)
- Final technology selection with rationale

**Success Criteria**:
- Selected models fit in 8GB VRAM with <5s inference latency
- Documented accuracy degradation from quantization <5%
- Technology choices justified with empirical data

#### Activity 2.3: Context Acquisition Survey Design and Database Schema (Week 7-8)

**Tasks**:
- Design onboarding survey (question structure, branching logic)
- Create schema for context storage (vector DB + metadata registry)
- Design few-shot example template and storage format
- Plan synthetic data generation pipeline

**Deliverables**:
- Context acquisition survey (final version)
- Database schema design (ERD for metadata, vector collection specs)
- Few-shot example template with 10+ seed examples
- Synthetic data generation plan (rule templates, LLM prompts)

**Success Criteria**:
- Survey covers all necessary context domains (business, technical, terminology)
- Schema supports efficient retrieval (<100ms for context lookup)
- Few-shot template validated with 3+ manual examples

**Phase 2 Milestone**: Complete architecture design, technology stack validated, context acquisition strategy defined.

---

### 11.4 Phase 3: Solution Development (Weeks 9-12)

**Aligned with Specific Objective 3**

#### Activity 3.1: Core Infrastructure and Context Manager (Week 9)

**Tasks**:
- Set up project repository structure
- Implement database connections (PostgreSQL/SQLite)
- Develop Context Manager Agent
  - Vector database integration
  - Embedding generation pipeline
  - Context retrieval with similarity search
- Implement survey processing logic

**Deliverables**:
- Git repository with organized structure
- Working Context Manager module with tests
- 100+ embedded context examples (from sample survey responses)
- Unit tests achieving >80% coverage for Context Manager

**Success Criteria**:
- Context retrieval returns relevant snippets for test queries (<100ms)
- Survey processing extracts entities correctly (>90% accuracy on sample)

#### Activity 3.2: Query Understanding and SQL Generation Agents (Week 10-11)

**Tasks**:
- Implement Query Understanding Agent
  - NER for entity extraction
  - Intent classification
  - Ambiguity detection rules
  - Clarification question generation
- Implement SQL Generator Agent
  - Prompt template design
  - LLM inference pipeline
  - Constrained decoding (syntax enforcement)
  - Few-shot example retrieval integration
- Generate synthetic training data (500-1000 examples)
- Fine-tune models using QLoRA

**Deliverables**:
- Query Understanding Agent with tests
- SQL Generator Agent with tests
- Synthetic dataset (500+ query-SQL pairs)
- Fine-tuned Code Llama 13B and Mistral 7B models
- Fine-tuning training logs and validation metrics

**Success Criteria**:
- Query Understanding correctly identifies intent for >85% of test queries
- SQL Generator produces syntactically valid SQL for >95% of inputs
- Fine-tuned models show >10% improvement over base models on validation set

#### Activity 3.3: Verification, Visualization, Session Manager, and Orchestration (Week 11-12)

**Tasks**:
- Implement Verification Agent (three layers)
  - Syntax validator
  - Semantic equivalence checker
  - Result sanity checker
  - Auto-correction engine
- Implement Visualization Engine
  - Chart type selection logic
  - Recharts integration
  - Statistical overlay generation
- Implement Session Manager Agent
  - PostgreSQL session storage with JSONB
  - Save/load/list/delete/export operations
  - Full-text search on session metadata
  - Session UI components (save dialog, session library)
- Implement Multi-Agent Orchestrator
  - LangGraph workflow definition
  - State management with multi-turn support
  - Progress tracking and WebSocket updates
  - Query cancellation handling
  - Error handling and retry logic
- Develop web interface
  - Keyword-assisted query builder UI
  - Visualization dashboard
  - Clarification dialogue components
  - Progress indicators with estimated completion times
  - Session controls (save, load, browse)
  - Real-time WebSocket connection for progress updates

**Deliverables**:
- Verification Agent with comprehensive test suite
- Visualization Engine with 5+ chart types supported
- Session Manager with database schema and full CRUD operations
- Multi-Agent Orchestrator coordinating all 7 modules with progress tracking
- Functional web interface (React frontend) with WebSocket support
- End-to-end integration tests including multi-turn conversations

**Success Criteria**:
- Verification detects >90% of semantic errors with <10% false positives
- Visualization correctly selects chart type for >85% of result sets
- Session save/load operations complete successfully with full context restoration
- Progress indicators update in real-time with <200ms latency
- Query cancellation works reliably for long-running operations
- Orchestrator successfully routes queries through appropriate workflow paths
- Web interface loads and processes queries end-to-end with progress visibility

**Phase 3 Milestone**: Fully functional prototype system, all modules implemented and tested, basic UI operational.

---

### 11.5 Phase 4: Results Analysis (Weeks 13-16)

**Aligned with Specific Objective 4**

#### Activity 4.1: Quantitative Evaluation and Benchmarking (Week 13-14)

**Tasks**:
- Execute benchmark evaluation (Spider, BIRD, custom test set)
- Measure quantitative metrics
  - Execution Accuracy (EX)
  - Exact Match Accuracy (EM)
  - Latency (mean, p50, p90, p99)
  - Resource utilization (RAM, VRAM, CPU)
- Perform ablation studies (remove modules, measure impact)
- Compare against baseline methods (commercial tools, academic benchmarks)

**Deliverables**:
- Comprehensive benchmark results report (10-15 pages)
- Performance metrics table with statistical significance testing
- Ablation study results (contribution of each module)
- Comparative analysis vs. 2-3 baseline systems

**Success Criteria**:
- Achieved >85% execution accuracy on domain-specific test set
- Average query latency <5 seconds for 90% of queries
- Demonstrated performance competitive with commercial solutions

#### Activity 4.2: User Study and Qualitative Evaluation (Week 14-15)

**Tasks**:
- Design user study protocol (tasks, questionnaires)
- Recruit 10-15 participants (professors, local business managers if feasible)
- Conduct task-based evaluation sessions
- Administer System Usability Scale (SUS) questionnaire
- Collect qualitative feedback (interviews, open-ended responses)
- Expert review: Database administrators assess SQL quality

**Deliverables**:
- User study protocol document
- Task success rate analysis
- SUS score report with statistical analysis
- Qualitative feedback summary (themes, pain points)
- Expert review report on SQL quality and optimization

**Success Criteria**:
- Task completion rate >75% for realistic scenarios
- SUS score >70 (acceptable usability)
- Identified 3-5 concrete improvement recommendations from feedback

**Note**: If recruiting external participants proves infeasible, conduct heuristic evaluation with thesis advisor and peers as alternative.

#### Activity 4.3: Thesis Documentation and Final Presentation (Week 15-16)

**Tasks**:
- Write thesis chapters (Introduction, Background, Methodology, Results, Discussion, Conclusion)
- Finalize all diagrams and figures
- Revise and polish based on advisor feedback
- Prepare final presentation slides
- Create demonstration video showcasing system capabilities
- Prepare GitHub repository for public release (if desired)

**Deliverables**:
- Complete thesis document (100-120 pages)
- Final presentation slides (20-30 slides)
- 5-10 minute demonstration video
- Public GitHub repository with README and documentation (optional)
- Poster for thesis defense (if required)

**Success Criteria**:
- Thesis document approved by advisor
- All figures and tables publication-ready
- Presentation effectively communicates contributions and results

**Phase 4 Milestone**: Thesis successfully defended, all deliverables completed, system evaluated and documented.

---

### 11.6 Risk Contingency Plans

**Risk 1: Model accuracy below target (< 85%)**
- **Mitigation**: Expand synthetic training data, try alternative models, simplify to subset of query types
- **Contingency Time**: 1 week buffer in Phase 3

**Risk 2: Hardware insufficient for selected models**
- **Mitigation**: Use smaller models (7B instead of 13B), increase quantization aggressiveness, cloud fallback
- **Contingency Time**: Resolved in Phase 2 technology validation

**Risk 3: User study recruitment fails**
- **Mitigation**: Substitute with heuristic evaluation, cognitive walkthrough with peers
- **Contingency Time**: No impact on timeline

**Risk 4: Integration issues between modules**
- **Mitigation**: Incremental integration testing throughout Phase 3, maintain clear interface contracts
- **Contingency Time**: 1 week buffer between Phases 3 and 4

---

## 12. Evaluation Plan

### 12.1 Quantitative Evaluation

#### 12.1.1 SQL Generation Accuracy

**Metric 1: Execution Accuracy (EX)**
- **Definition**: Percentage of generated SQL queries that produce correct results
- **Calculation**: 
  ```
  EX = (# queries with correct results) / (total # queries) × 100%
  ```
- **Gold Standard**: Ground-truth results from benchmark datasets
- **Target**: **>90% on domain-specific test set, >85% on cross-domain benchmarks**

**Metric 2: Exact Match Accuracy (EM)**
- **Definition**: Percentage of generated SQL exactly matching gold-standard SQL (modulo formatting)
- **Calculation**:
  ```
  EM = (# exact SQL matches) / (total # queries) × 100%
  ```
- **Note**: More stringent than EX; multiple SQL can produce same results
- **Target**: **>70% on benchmarks** (EM typically 10-20% lower than EX)

**Evaluation Protocol**:
1. Execute generated SQL and gold-standard SQL on same database
2. Compare result sets (order-agnostic, type-normalized)
3. For EX: Mark correct if results identical
4. For EM: Canonicalize SQL (normalize whitespace, keyword casing) and compare strings

#### 12.1.2 Verification System Performance

**Metric 3: Error Detection Rate (Recall)**
- **Definition**: Percentage of erroneous SQL queries correctly flagged by verification
- **Calculation**:
  ```
  Recall = True Positives / (True Positives + False Negatives)
  ```
- **Target**: **>95% error detection**

**Metric 4: False Positive Rate**
- **Definition**: Percentage of correct SQL incorrectly flagged as erroneous
- **Calculation**:
  ```
  FPR = False Positives / (False Positives + True Negatives)
  ```
- **Target**: **<5% false alarms**

**Evaluation Protocol**:
1. Collect 200+ test cases with known correctness labels
2. Run verification pipeline on all test cases
3. Compare verification decisions with ground truth
4. Calculate confusion matrix and derive metrics

#### 12.1.3 System Performance

**Metric 5: Query Processing Latency**
- **Measurements**:
  - **Mean latency**: Average processing time across all queries
  - **Median (p50)**: 50th percentile latency
  - **p90, p99**: 90th and 99th percentile (tail latencies)
- **Target**: 
  - **Mean <3 seconds, p90 <5 seconds** for simple queries (single table, basic aggregation)
  - **p99 <10 seconds** for complex queries (multi-table joins, nested subqueries)

**Metric 6: Resource Utilization**
- **Measurements**:
  - Peak RAM usage during inference
  - Peak VRAM usage during inference
  - Average CPU utilization
- **Target**:
  - **RAM <12GB, VRAM <7GB** (leaving headroom on 16GB/8GB system)
  - **CPU <70% average** (leaving capacity for concurrent processes)

**Metric 7: Progress Communication Effectiveness**
- **Measurements**:
  - Progress update latency (time between processing phase change and UI update)
  - User satisfaction with progress indicators (survey question: 1-5 scale)
  - Query cancellation success rate
- **Target**:
  - **Progress update latency <200ms**
  - **User satisfaction >4/5**
  - **Cancellation success rate >95%**

**Metric 8: Session Management Performance**
- **Measurements**:
  - Session save time (average time to persist session to database)
  - Session load time (average time to restore full context)
  - Session search response time (full-text search on metadata)
  - Session usage rate (percentage of multi-query investigations that get saved)
- **Target**:
  - **Save time <1 second**
  - **Load time <2 seconds**
  - **Search response <500ms**
  - **Usage rate >30% of multi-turn conversations**

**Evaluation Protocol**:
1. Profile system with `nvidia-smi` (GPU), `psutil` (RAM/CPU)
2. Execute 100+ diverse queries and record metrics
3. Analyze distribution and identify bottlenecks

#### 12.1.4 Ambiguity Resolution Effectiveness

**Metric 7: Clarification Success Rate**
- **Definition**: Percentage of ambiguous queries successfully resolved through clarification dialogue
- **Calculation**:
  ```
  CSR = (# resolved ambiguities) / (# detected ambiguities) × 100%
  ```
- **Target**: **>85% resolution success**

**Metric 8: Average Clarification Turns**
- **Definition**: Mean number of clarification questions required per ambiguous query
- **Target**: **<2 turns for 80% of ambiguous queries**

**Evaluation Protocol**:
1. Curate 50+ intentionally ambiguous queries
2. Run queries through system, tracking clarification dialogues
3. Assess whether final resolved query matches intended meaning
4. Count clarification turns required

### 12.2 Qualitative Evaluation

#### 12.2.1 Usability Assessment

**System Usability Scale (SUS)**
- **Description**: Standardized 10-item questionnaire measuring perceived usability
- **Scale**: Likert scale (1-5) for each item
- **Scoring**: Converts to 0-100 scale
- **Interpretation**:
  - <50: Poor usability
  - 50-70: Marginal usability
  - 70-85: Good usability
  - >85: Excellent usability
- **Target**: **SUS score >70** (good usability threshold)

**Questionnaire Items** (abbreviated):
1. I think I would like to use this system frequently
2. I found the system unnecessarily complex (reverse-scored)
3. I thought the system was easy to use
4. I think I would need technical support to use this system (reverse-scored)
5. I found the various functions in the system well integrated
[... 5 more items]

**Evaluation Protocol**:
1. After user completes tasks, administer SUS questionnaire
2. Calculate SUS score per participant
3. Compute mean and standard deviation across participants
4. Perform statistical significance testing vs. baseline (if available)

#### 12.2.2 Task-Based Evaluation

**Scenarios** (5 representative tasks):
1. **Simple Aggregation**: "What was our total revenue last quarter?"
2. **Trend Analysis**: "Show me monthly sales over the past year"
3. **Comparative Analysis**: "Which region had the highest growth rate last year?"
4. **Multi-dimensional**: "Break down revenue by product category and region for Q3 2024"
5. **Exploratory**: "Show me top performing products, then drill down into their regional distribution"

**Metrics**:
- **Task Completion Rate**: Percentage of tasks successfully completed
- **Time on Task**: Average time to complete each task
- **Error Rate**: Number of incorrect attempts before success
- **User Confidence**: Self-reported confidence in results (1-5 scale)

**Target**: 
- **>75% task completion rate**
- **<5 minutes average per task**
- **>4/5 confidence rating**

#### 12.2.3 Expert Review

**SQL Quality Assessment** (by database administrators or SQL experts):
- **Correctness**: Does SQL accurately capture query intent?
- **Efficiency**: Is SQL optimized (proper indexes usage, join order)?
- **Style**: Does SQL follow best practices (readable, maintainable)?
- **Security**: Are there injection vulnerabilities or dangerous operations?

**Rating Scale**: 1-5 for each criterion

**Target**: **>4/5 average rating across criteria**

### 12.3 Comparative Analysis

**Baselines**:
1. **Commercial Tools**: Tableau Ask Data, Power BI Q&A (using public benchmarks)
2. **Academic Baselines**: Published results on Spider/BIRD (DIN-SQL, RESDSQL, C3)
3. **Zero-shot LLM**: GPT-3.5/GPT-4 with few-shot prompting (no fine-tuning)

**Comparison Dimensions**:
- Execution Accuracy on shared benchmark
- Latency (when measurable)
- Cost (API calls vs. local inference)
- Ambiguity handling capability
- Visualization integration

**Expected Outcome**: Demonstrate competitive accuracy with advantages in cost-efficiency, ambiguity resolution, and verification robustness.

---

## 13. Expected Results

### 13.1 Technical Achievements

**Primary Deliverable**: Functional IDI system with seven integrated modules achieving target performance metrics.

**Quantitative Targets**:
- **Execution Accuracy**: 90-95% on domain-specific queries, 85-90% on cross-domain benchmarks
- **Latency**: <30 seconds for complex queries with progress indicators, <5 seconds for simple queries
- **Verification Performance**: >95% error detection, <5% false positives
- **Ambiguity Resolution**: >85% success rate, <2 average clarification turns
- **Multi-Turn Support**: 90% success rate for 3+ turn conversations, 80% feedback accuracy
- **Progress Communication**: <200ms update latency, >95% cancellation success rate
- **Session Management**: <1s save time, <2s load time, >30% usage rate
- **Usability**: SUS score >70

**Qualitative Outcomes**:
- Demonstrated usability for non-technical users through user study
- Expert validation of SQL quality and system robustness
- Identified concrete improvement pathways for future work

### 13.2 Academic Contributions

1. **Context Acquisition Framework**: First systematic study of survey-based domain knowledge acquisition for NL2SQL, providing reusable methodology for enterprise deployment.

2. **Hybrid Ambiguity Resolution**: Novel combination of keyword-guided interfaces and conversational clarification, bridging HCI and NLP perspectives.

3. **Multi-layer Verification**: Extension of verification beyond syntax to semantic equivalence and result sanity, advancing NL2SQL trustworthiness.

4. **Resource-Constrained Optimization**: Demonstration that modular architecture with specialized lightweight models rivals monolithic large models, challenging scalability assumptions.

5. **Empirical Insights**: Detailed ablation studies quantifying contribution of each module, informing future architectural decisions.

### 13.3 Practical Impact

**For Non-Technical Users**:
- Reduction in data access barriers, enabling self-service analytics
- Increased data literacy through transparent SQL generation
- Faster decision-making (minutes vs. hours/days)

**For Organizations**:
- Cost savings by reducing analyst dependency for routine queries
- Reallocation of technical resources to high-value tasks
- Competitive advantage through agile data-driven strategy adaptation

**For Research Community**:
- Open-source reference implementation demonstrating practical NL2SQL deployment
- Benchmark results establishing new baselines
- Identified research directions for future investigation

### 13.4 Publication Potential

**Target Venues** (post-thesis):
- **Conferences**: VLDB, SIGMOD, ACL (NLP), KDD (data mining)
- **Workshops**: NL2SQL workshop, Data Management for End-Users
- **Journals**: ACM TODS, IEEE TKDE, Journal of Database Management

**Publishable Contributions**:
- Architecture and methodology (system paper)
- Evaluation results and comparative analysis (benchmark paper)
- Context acquisition framework (short paper or workshop)

---

## 14. Risk Analysis and Mitigation

### 14.1 Technical Risks

**Risk 1: LLM Accuracy Below Target**
- **Probability**: Medium (30-40%)
- **Impact**: High (core functionality)
- **Mitigation**:
  - Expand synthetic training data generation (increase diversity)
  - Experiment with alternative models (DeepSeek Coder, Phi-3)
  - Narrow scope to subset of query types (e.g., focus on aggregation, defer multi-table joins)
  - Ensemble approach (generate multiple candidates, vote)
- **Contingency**: Accept lower accuracy target (80-85%) and discuss limitations

**Risk 2: Insufficient Computational Resources**
- **Probability**: Low (15-20%) [mitigated by Phase 2 validation]
- **Impact**: High (prevents local deployment)
- **Mitigation**:
  - Further quantization (3-bit, or CPU-only with llama.cpp)
  - Use smaller models (7B instead of 13B for all agents)
  - Cloud fallback for SQL generation only (minimize API costs)
  - Optimize inference (caching, batching, prompt compression)
- **Contingency**: Hybrid deployment (Query Understanding local, SQL Generation cloud)

**Risk 3: Verification System High False Positive Rate**
- **Probability**: Medium (25-35%)
- **Impact**: Medium (user frustration from blocked correct queries)
- **Mitigation**:
  - Calibrate verification thresholds using validation set
  - Provide override mechanism (user can force execution with warning)
  - Collect false positive cases for model retraining
- **Contingency**: Relax verification to syntax-only layer, defer semantic checking

**Risk 4: Integration Complexity**
- **Probability**: Medium (30-40%)
- **Impact**: Medium (delays, debugging overhead)
- **Mitigation**:
  - Maintain clear module interfaces with type contracts
  - Incremental integration (test each module independently before connecting)
  - Comprehensive logging and error handling
  - Use integration testing throughout Phase 3
- **Contingency**: Simplify integration (reduce module count, merge related components)

**Risk 5: WebSocket Connection Stability**
- **Probability**: Low-Medium (20-30%)
- **Impact**: Medium (broken progress updates, poor UX)
- **Mitigation**:
  - Implement automatic reconnection logic with exponential backoff
  - Fallback to polling if WebSocket unavailable
  - Store progress state server-side for recovery after reconnection
  - Comprehensive error handling for connection drops
- **Contingency**: Use Server-Sent Events (SSE) for one-way updates, disable cancellation feature

**Risk 6: Session Storage Performance Degradation**
- **Probability**: Low (15-20%)
- **Impact**: Low-Medium (slow session operations)
- **Mitigation**:
  - Proper database indexing (GIN indexes on JSONB, tags, timestamps)
  - Limit result snapshot size (truncate large datasets)
  - Implement pagination for session lists
  - Cache frequently accessed sessions
- **Contingency**: Switch to MongoDB for better document storage performance, implement session archiving

### 14.2 Project Management Risks

**Risk 7: Scope Creep**
- **Probability**: High (50-60%) [common in thesis projects]
- **Impact**: Medium (timeline delays)
- **Mitigation**:
  - Strict prioritization: Core modules first, enhancements only if time permits
  - Weekly progress reviews with advisor to maintain focus
  - Define MVP clearly in Phase 1
- **Contingency**: Cut nice-to-have features (advanced visualizations, dashboard composition)

**Risk 8: Timeline Slippage**
- **Probability**: Medium (35-45%)
- **Impact**: High (missed defense deadline)
- **Mitigation**:
  - Build 1-week buffer between Phases 3 and 4
  - Parallel development where possible (frontend + backend)
  - Early start (before semester begins, as mentioned)
  - Bi-weekly checkpoint meetings
- **Contingency**: Reduce evaluation scope (skip user study, rely on benchmarks + heuristic evaluation)

**Risk 9: Advisor Availability Limited**
- **Probability**: Low (10-20%)
- **Impact**: Medium (feedback delays)
- **Mitigation**:
  - Establish regular meeting schedule early
  - Prepare concise progress reports for efficient reviews
  - Leverage university resources (writing center, peer review)
- **Contingency**: Seek co-advisor or senior PhD student mentorship

### 14.3 External Risks

**Risk 10: Benchmark Dataset Access Issues**
- **Probability**: Low (5-10%)
- **Impact**: Medium (evaluation limitations)
- **Mitigation**:
  - Download datasets early in Phase 1
  - Maintain local backups
  - Have alternative benchmarks identified
- **Contingency**: Use only publicly available benchmarks + custom test set

**Risk 11: User Study Recruitment Failure**
- **Probability**: Medium (30-40%) [especially in academic environment]
- **Impact**: Low (alternative evaluation methods exist)
- **Mitigation**:
  - Recruit early (Week 10-11)
  - Offer incentives (coffee gift cards, lottery for larger prize)
  - Leverage advisor networks (professors, local businesses)
- **Contingency**: Substitute with heuristic evaluation, cognitive walkthrough with peers (fully acceptable for thesis)

**Risk 12: Hardware Failure**
- **Probability**: Very Low (<5%)
- **Impact**: High (data loss, development halt)
- **Mitigation**:
  - Daily code commits to GitHub
  - Weekly full system backups to external drive/cloud
  - Docker containers ensure rapid environment recovery
- **Contingency**: Access to university GPU cluster or temporary cloud GPU rental

---

## 15. References

Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... & Amodei, D. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems*, 33, 1877-1901.

Floratou, A., Psallidas, F., Zhao, F., Deep, S., Hagleither, G., Tan, W., ... (2024). NL2SQL is a solved problem... Not! In *Conference on Innovative Data Systems Research (CIDR)*.

Gao, D., Wang, H., Li, Y., Sun, X., Qian, Y., Ding, B., & Zhou, J. (2024). Text-to-SQL empowered by large language models: A benchmark evaluation. *Proceedings of the VLDB Endowment*, 17(5), 1132-1145.

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. *MIS Quarterly*, 28(1), 75-105.

Kumar, R., Fotherby, T., Keshavanarayana, S., Matthew, T., Vaquero, D., Varshneya, A., & Wu, J. (2025). Enterprise-grade natural language to SQL generation using LLMs: Balancing accuracy, latency, and scale. *AWS Machine Learning Blog*. Retrieved from https://aws.amazon.com/blogs/machine-learning/

Lei, W., Wang, W., Ma, Z., Gan, T., Lu, W., Kan, M. Y., & Chua, T. S. (2020). Re-examining the role of schema linking in Text-to-SQL. In *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)* (pp. 6943-6954).

Li, B., Luo, Y., Zhu, Y., Lin, Y., Chai, C., Gu, Z., ... & Tang, N. (2024). The dawn of natural language to SQL: Are we fully ready? *Proceedings of the VLDB Endowment*, 17(11), 3318-3331.

Li, H., Zhang, J., Liu, H., Fan, J., Zhang, X., Zhu, J., ... & Chen, H. (2024). CodeS: Towards building open-source language models for text-to-SQL. *arXiv preprint arXiv:2402.16347*.

Li, J., Hui, B., Cheng, R., Qin, B., Ma, C., Huo, N., ... & Li, Y. (2023). Can LLM already serve as a database interface? A BIg bench for large-scale database grounded Text-to-SQLs. *arXiv preprint arXiv:2305.03111*.

Li, B., Zhang, J., Fan, J., Xu, Y., Chen, C., Tang, N., & Luo, Y. (2025). Alpha-SQL: Zero-shot text-to-SQL using Monte Carlo tree search. *arXiv preprint arXiv:2502.17248*.

Liu, X., Shen, S., Li, B., Tang, N., & Luo, Y. (2025). NL2SQL-BUGs: A benchmark for detecting semantic errors in NL2SQL translation. *arXiv preprint arXiv:2503.11984*.

Luo, Y., Li, G., Fan, J., Chai, C., & Tang, N. (2025). Natural language to SQL: State of the art and open problems. *Proceedings of the VLDB Endowment*, 18(12), 5466-5471. https://doi.org/10.14778/3750601.3750696

Mackinlay, J. (1986). Automating the design of graphical presentations of relational information. *ACM Transactions on Graphics*, 5(2), 110-141.

Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar, G. T., ... & Arik, S. O. (2024). CHASE-SQL: Multi-path reasoning and preference optimized candidate selection in text-to-SQL. *arXiv preprint arXiv:2410.01943*.

Schlögl, S., Doherty, G., & Luz, S. (2016). Peer involvement in asynchronous question and answer forums for software development. *Interacting with Computers*, 28(6), 828-849.

Scholak, T., Schucher, N., & Bahdanau, D. (2021). PICARD: Parsing incrementally for constrained auto-regressive decoding from language models. *arXiv preprint arXiv:2109.05093*.

Talaei, S., Pourreza, M., Chang, Y. C., Mirhoseini, A., & Saberi, A. (2024). CHESS: Contextual harnessing for efficient SQL synthesis. *arXiv preprint arXiv:2405.16755*.

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, 30, 5998-6008.

Wang, B., Shin, R., Liu, X., Polozov, O., & Richardson, M. (2020). RAT-SQL: Relation-aware schema encoding and linking for text-to-SQL parsers. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 7567-7578).

Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., ... & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, 35, 24824-24837.

Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., ... & Radev, D. (2018). Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-SQL task. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing* (pp. 3911-3921).

Zelle, M., & Mooney, R. J. (1996). Learning to parse database queries using inductive logic programming. In *Proceedings of the Thirteenth National Conference on Artificial Intelligence* (pp. 1050-1055).

---

## Appendices

### Appendix A: Glossary of Terms

- **NL2SQL**: Natural Language to SQL, the task of translating natural language queries into SQL
- **LLM**: Large Language Model, neural networks with billions of parameters trained on vast text corpora
- **PLM**: Pre-trained Language Model, models like BERT and T5 trained on general text
- **Schema Linking**: Mapping natural language phrases to database schema elements (tables, columns)
- **Execution Accuracy (EX)**: Percentage of queries producing correct results
- **Exact Match (EM)**: Percentage of queries matching gold-standard SQL exactly
- **QLoRA**: Quantized Low-Rank Adaptation, parameter-efficient fine-tuning technique
- **Agentic Workflow**: System where specialized agents collaborate to accomplish complex tasks

### Appendix B: Example Queries and SQL

**Example 1: Simple Aggregation**
- **NL**: "What was our total revenue last quarter?"
- **SQL**: 
  ```sql
  SELECT SUM(total_amount) AS total_revenue
  FROM orders
  WHERE order_date BETWEEN '2024-07-01' AND '2024-09-30';
  ```

**Example 2: Multi-table Join with Grouping**
- **NL**: "Show me top 5 customers by revenue in 2024"
- **SQL**:
  ```sql
  SELECT c.name, SUM(o.total_amount) AS revenue
  FROM customers c
  JOIN orders o ON c.id = o.customer_id
  WHERE EXTRACT(YEAR FROM o.order_date) = 2024
  GROUP BY c.id, c.name
  ORDER BY revenue DESC
  LIMIT 5;
  ```

**Example 3: Temporal Trend Analysis**
- **NL**: "Show monthly sales trend over the past year"
- **SQL**:
  ```sql
  SELECT 
    DATE_TRUNC('month', order_date) AS month,
    SUM(total_amount) AS monthly_sales
  FROM orders
  WHERE order_date >= CURRENT_DATE - INTERVAL '1 year'
  GROUP BY DATE_TRUNC('month', order_date)
  ORDER BY month;
  ```

### Appendix C: System Architecture Diagrams

[Reference diagrams to be created during implementation]

**Diagram C.1**: Component Architecture (high-level module relationships)  
**Diagram C.2**: Deployment Architecture (Docker containers, services)  
**Diagram C.3**: Sequence Diagram - Query Processing Workflow  
**Diagram C.4**: Sequence Diagram - Clarification Dialogue  
**Diagram C.5**: Entity-Relationship Diagram - Context Storage Schema  
**Diagram C.6**: Data Flow Diagram - End-to-End Query Execution  

### Appendix D: Survey Template

[Context Acquisition Survey - Full Version]

**Section A: Business Context**
1. What industry does your organization operate in? [Dropdown]
2. What are your primary business functions? [Multi-select: Sales, Operations, Finance, HR, Marketing, Other]
3. What key performance indicators (KPIs) do you track? [Free text]
4. What are your most common reporting needs? [Multi-select + Free text]
5. How frequently do you need to query data? [Daily/Weekly/Monthly/Ad-hoc]

**Section B: Technical Schema**
6. What database system do you use? [PostgreSQL/MySQL/SQL Server/Oracle/Other]
7. Upload your database schema (DDL file): [File upload]
8. Describe key tables and their purposes: [Guided form]
9. Approximately how many rows are in your largest tables? [<1K, 1K-100K, 100K-1M, >1M]
10. How frequently is data updated? [Real-time/Hourly/Daily/Weekly]

**Section C: Domain Terminology**
11. Provide a business glossary (term → definition → related data): [Table input]
12. Are there synonyms for key metrics? [e.g., "revenue" = "sales"]: [Table input]
13. When does your fiscal year start? [Date picker]
14. What are your standard reporting periods? [Quarterly/Monthly/Custom]

[... continues with 20 total questions]

### Appendix E: Code Snippets

[Representative code samples demonstrating key implementation patterns]

**E.1: Context Retrieval with ChromaDB**
```python
def retrieve_relevant_context(query: str, top_k: int = 3) -> List[str]:
    """Retrieve most relevant context snippets for a query."""
    query_embedding = embedding_model.encode([query])
    results = context_collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k
    )
    return results['documents'][0]
```

**E.2: LLM Inference with Quantization**
```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

def load_quantized_model(model_name: str):
    """Load 4-bit quantized model."""
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map="auto"
    )
    return model
```

**E.3: SQL Verification - Syntax Layer**
```python
def verify_sql_syntax(sql: str, dialect: str = "postgresql") -> ValidationResult:
    """Verify SQL syntax correctness."""
    try:
        parsed = sqlparse.parse(sql)[0]
        
        # Check for dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT']
        if any(kw in sql.upper() for kw in dangerous_keywords):
            return ValidationResult(
                valid=False, 
                error="Mutation statements not allowed"
            )
        
        return ValidationResult(valid=True)
    except Exception as e:
        return ValidationResult(valid=False, error=str(e))
```

---

**Document Information**

- **Title**: IDI (Intelligent Database Interface): Contextual NL2SQL System for Executive Decision Support - Project Documentation
- **Author**: [Your Name]
- **Advisor**: [Advisor Name]
- **Institution**: Universidad Nacional de Colombia
- **Program**: Computer and Systems Engineering
- **Version**: 1.0
- **Date**: [Current Date]
- **Status**: Draft for Review

---

**End of Document**