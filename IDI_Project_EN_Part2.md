# IDI (Intelligent Database Interface): Contextual NL2SQL System for Executive Decision Support

## Project Documentation - Computer and Systems Engineering Thesis - PART 2
### Universidad Nacional de Colombia

**For sections 1-8, see IDI_Project_EN_Part1.md**

---

## Table of Contents (Part 2)

9. [Technical Approach by Challenge](#9-technical-approach-by-challenge)
10. [Technology Stack Analysis](#10-technology-stack-analysis)
11. [Implementation Plan](#11-implementation-plan)
12. [Evaluation Plan](#12-evaluation-plan)
13. [Expected Results](#13-expected-results)
14. [Risk Analysis and Mitigation](#14-risk-analysis-and-mitigation)
15. [References](#15-references)

---

## 9. Technical Approach by Challenge

### 9.1 Challenge: Domain Knowledge Gap

**Problem**: General-purpose LLMs lack enterprise-specific schema understanding, business logic, and terminology, leading to incorrect query generation.

**IDI Solution**: **Structured Context Acquisition System**

#### Component 1: Onboarding Survey Design

**Survey Structure** (3 sections, ~20 questions):

**Section A: Business Context**
- Industry/sector (dropdown)
- Primary business functions (checkboxes: sales, operations, finance, HR)
- Key performance indicators (free text + examples)
- Common reporting needs (multiple choice + free text)

**Section B: Technical Schema**
- Database type and dialect (PostgreSQL, MySQL, SQL Server, Oracle)
- Schema upload (DDL file or connection string for inspection)
- Key tables and relationships (guided form)
- Data distribution characteristics (approximate row counts, update frequency)

**Section C: Domain Terminology**
- Business glossary (term → definition → related tables/columns)
- Synonym mapping (e.g., "revenue" = "sales" = "total_amount")
- Temporal conventions (fiscal year start, standard reporting periods)

**Survey Processing**:
1. Extract structured entities (tables, columns, metrics)
2. Generate embeddings for free-text responses (business logic, glossary)
3. Store in vector database for semantic retrieval
4. Create metadata registry linking terms to schema elements

#### Component 2: Schema Metadata Augmentation

Following AWS-Cisco pattern (Kumar et al., 2025), augment DDL with:

```sql
-- Original DDL
CREATE TABLE orders (
  order_id INT PRIMARY KEY,
  customer_id INT,
  order_date DATE,
  total_amount DECIMAL(10,2)
);

-- Augmented with comments
CREATE TABLE orders (
  order_id INT PRIMARY KEY,  -- Unique identifier for each order
  customer_id INT,           -- Foreign key to customers.id
  order_date DATE,           -- Date order was placed (not shipped)
  total_amount DECIMAL(10,2) -- Total order value in USD, including tax
) COMMENT 'Transactional records of customer purchases';

-- Join hints
/* When joining orders with customers, prefer INNER JOIN 
   unless specifically analyzing missing customer data */
```

#### Component 3: Few-Shot Example Library

Maintain domain-specific query examples:

```json
{
  "domain": "sales_analytics",
  "examples": [
    {
      "nl": "What were total sales in Q2 2024?",
      "sql": "SELECT SUM(total_amount) FROM orders WHERE order_date BETWEEN '2024-04-01' AND '2024-06-30';",
      "explanation": "Quarterly aggregation with date range filtering"
    },
    {
      "nl": "Show top 5 customers by revenue last year",
      "sql": "SELECT c.name, SUM(o.total_amount) AS revenue FROM customers c JOIN orders o ON c.id = o.customer_id WHERE EXTRACT(YEAR FROM o.order_date) = 2023 GROUP BY c.id, c.name ORDER BY revenue DESC LIMIT 5;",
      "explanation": "Multi-table join with aggregation and ranking"
    }
  ]
}
```

**Retrieval Strategy**: Given new query, use semantic similarity (cosine distance in embedding space) to retrieve top-k most relevant examples for prompt context.

#### Component 4: Continuous Learning

- **Query Log Analysis**: Identify frequently asked question patterns
- **Correction Learning**: When users modify generated SQL, store correction as new training example
- **Schema Evolution Tracking**: Detect DDL changes and update metadata

**Expected Impact**: 20-30% accuracy improvement over zero-shot baseline through domain-specific grounding.

---

### 9.2 Challenge: Natural Language Ambiguity

**Problem**: Executive queries often contain underspecification (missing parameters), synonymy (multiple terms for same concept), and context-dependence (referencing previous results).

**IDI Solution**: **Hybrid Keyword Guidance + Clarification Dialogue**

#### Component 1: Keyword-Assisted Query Builder

**Interface Design**:

```
┌────────────────────────────────────────────────┐
│  Query Builder                                 │
├────────────────────────────────────────────────┤
│  Statistical Operation:                        │
│  [Average ▼] [Sum] [Count] [Median] [Trend]    │
│                                                 │
│  Metric:                                        │
│  [revenue ▼] [units_sold] [profit_margin]      │
│                                                 │
│  Grouping (optional):                           │
│  [region ▼] [product_category] [department]    │
│                                                 │
│  Time Period:                                   │
│  [Q3 2024 ▼] [Custom Range: 📅 - 📅]           │
│                                                 │
│  Additional Filters:                            │
│  [+ Add Condition]                              │
│                                                 │
│  Natural Language (optional):                   │
│  [I want to see ___________________________]   │
│                                                 │
│  [Generate Query]                               │
└────────────────────────────────────────────────┘
```

**Keyword Sources**:
1. **Statistical operations** (pre-defined): Average, Sum, Count, Median, Std Dev, Min, Max, Percentile, Growth Rate, YoY Change
2. **Schema-derived**: Extracted from column names (e.g., `total_amount` → "revenue", "sales")
3. **Context-derived**: Terms from business glossary survey responses
4. **Administrative**: Quarter, Fiscal Year, Region, Department, Product Line

**Benefits**:
- **Reduced ambiguity**: Structured inputs eliminate 60-70% of underspecification
- **Faster input**: Dropdown selection faster than typing for common operations
- **Discoverability**: Users learn available metrics through interface exploration

#### Component 2: Ambiguity Detection Rules

When free-form NL query used, apply detection heuristics:

**Rule 1: Missing Temporal Scope**
- Trigger: Query contains time-relative terms ("last quarter", "this year") without explicit dates
- Action: Present date range selector with contextually relevant options

**Rule 2: Unclear Entity Reference**
- Trigger: Query mentions ambiguous term (e.g., "product" when both `product_name` and `product_category` exist)
- Action: Ask: "Did you mean: [Product Name] or [Product Category]?"

**Rule 3: Missing Aggregation**
- Trigger: Metric mentioned without statistical operation ("show revenue by region")
- Action: Ask: "How should revenue be calculated: [Sum] [Average] [Total Count of Orders]?"

**Rule 4: Underspecified Filter**
- Trigger: Conditional without value ("sales above threshold")
- Action: Request specific value or offer data-driven suggestion

#### Component 3: Clarification Dialogue Manager

**Design Principles**:
- **Maximum 3 clarifying questions** to avoid user frustration
- **Present options, don't ask open-ended** (e.g., "Which quarter: Q1/Q2/Q3/Q4?" not "What time period?")
- **Learn from history**: If user consistently selects "Q3" for "last quarter" queries in September, auto-infer

**Dialogue State Tracking**:
```python
class DialogueState:
    original_query: str
    detected_ambiguities: List[Ambiguity]
    clarifications_needed: List[Question]
    user_responses: Dict[str, Any]
    resolved_intent: Optional[StructuredIntent]
```

**Example Flow**:
```
User: "Show me performance last quarter"

System Detects:
- Ambiguity 1: "performance" (could be sales, profit, customer satisfaction)
- Ambiguity 2: "last quarter" (Q2 2024 or Q3 2024 depending on current date)

System Responds:
"I need a couple clarifications:
1. Which metric for performance: [Revenue] [Profit] [Units Sold]
2. Which quarter: [Q2 2024 (Apr-Jun)] [Q3 2024 (Jul-Sep)]"

User: "Revenue, Q3"

System: [Proceeds with resolved intent: revenue sum, Q3 2024 date range]
```

#### Component 4: Multi-Turn Context Preservation

**Session Management**:
- Store previous queries and results in session state
- Resolve pronouns and references ("Show me that by region" → "that" = previous metric)
- Enable progressive refinement ("Now break it down by product category")

**Entity Tracking**:
```python
class ConversationContext:
    turn_history: List[Turn]
    mentioned_entities: Set[str]  # Tracks referenced tables/columns
    last_metric: Optional[str]
    last_time_range: Optional[DateRange]
    last_results: Optional[DataFrame]
```

**Expected Impact**: 80-85% ambiguity resolution success rate with <2 average clarification turns.

---

### 9.3 Challenge: Schema Complexity

**Problem**: Enterprise databases have distributed architectures, nested structures, and complex join relationships requiring expert-level SQL.

**IDI Solution**: **Schema Federation + Data Abstractions**

#### Component 1: Relationship Documentation

During onboarding, explicitly map relationships:

```yaml
relationships:
  - type: one_to_many
    parent: customers
    child: orders
    join_condition: customers.id = orders.customer_id
    hint: "Use INNER JOIN for customer purchase analysis, LEFT JOIN to include customers without orders"
  
  - type: many_to_many
    table1: orders
    table2: products
    junction: order_items
    join_path: 
      - orders.id = order_items.order_id
      - order_items.product_id = products.id
```

**Prompt Integration**: Include relevant relationships in SQL generation prompt based on query intent.

#### Component 2: Abstract View Generation

For complex patterns, create temporary views:

**Example: Nested JSON column**

Original schema:
```sql
CREATE TABLE events (
  id INT,
  metadata JSON  -- Contains {user_id, action_type, timestamp, properties: {...}}
);
```

Abstraction:
```sql
CREATE TEMP VIEW event_details AS
SELECT 
  id,
  metadata->>'user_id' AS user_id,
  metadata->>'action_type' AS action_type,
  (metadata->>'timestamp')::timestamp AS event_time,
  metadata->'properties'->>'category' AS event_category
FROM events;
```

LLM now generates simple queries against `event_details` instead of complex JSON path navigation.

#### Component 3: Schema Pruning

For large schemas (100+ tables), reduce LLM attention burden:

1. **Domain Classification**: Categorize tables into domains (sales, inventory, HR)
2. **Relevance Scoring**: Given query, rank tables by relevance using:
   - Keyword overlap between query and table/column names
   - Historical usage patterns (frequently joined tables)
3. **Prompt Construction**: Include only top-k most relevant tables (k=5-10)

**Expected Impact**: 40-50% reduction in prompt length, 15-20% latency improvement.

---

### 9.4 Challenge: Multi-Turn Dialogue

**Problem**: Exploratory data analysis requires conversational sequences with context preservation and progressive refinement.

**IDI Solution**: **Stateful Conversation Manager**

#### Component 1: Dialogue State Machine

```
States:
- INITIAL: Fresh conversation, no context
- CLARIFYING: Awaiting user response to ambiguity questions
- EXECUTING: Query processing in progress
- RESULTS_READY: Displaying results, ready for follow-up
- ERROR: Handling query failure, offering retry

Transitions:
INITIAL --[query submitted]--> CLARIFYING (if ambiguities) | EXECUTING (if clear)
CLARIFYING --[user response]--> EXECUTING
EXECUTING --[success]--> RESULTS_READY | --[failure]--> ERROR
RESULTS_READY --[follow-up query]--> CLARIFYING | EXECUTING
ERROR --[retry/rephrase]--> CLARIFYING | EXECUTING
```

#### Component 2: Reference Resolution

**Pronoun Resolution**:
- "Show me their purchases" → "their" = customer segment from previous query
- "Break that down by month" → "that" = metric from last result

**Implementation**:
```python
def resolve_references(query: str, context: ConversationContext) -> str:
    # Replace pronouns with explicit references
    if "that" in query.lower() and context.last_metric:
        query = query.replace("that", f"the {context.last_metric}")
    
    # Inherit filters from previous query unless contradicted
    if not has_time_filter(query) and context.last_time_range:
        query += f" for {context.last_time_range}"
    
    return query
```

#### Component 3: Progressive Refinement

**Scenario**: User starts broad, narrows iteratively

```
Turn 1:
User: "Show me sales performance"
System: [Clarifies → Generates query for total sales]
Result: $10.5M total sales in Q3 2024

Turn 2:
User: "By region"
System: [Infers: GROUP BY region for the same metric and time period]
Result: Northeast $4.2M, Southeast $3.1M, West $2.7M, Midwest $0.5M

Turn 3:
User: "Northeast only, by product category"
System: [Infers: Same metric, Q3 2024, filter region='Northeast', GROUP BY product_category]
Result: Electronics $1.8M, Apparel $1.5M, Home Goods $0.9M
```

**Implementation**: Maintain modification stack, applying deltas to base query rather than regenerating from scratch.

#### Component 4: Result Caching

**Strategy**: Cache query results for session duration
- **Key**: Query fingerprint (canonicalized SQL + parameters)
- **Value**: Result DataFrame + metadata (execution time, row count)
- **Eviction**: LRU policy with 100MB session limit

**Benefit**: Sub-second response for repeated/similar queries

**Expected Impact**: 90% success rate for 3+ turn conversations.

---

### 9.5 Challenge: SQL Correctness Verification

**Problem**: Generated SQL may contain semantic errors (wrong aggregations, incorrect joins, missing filters) producing misleading results.

**IDI Solution**: **Three-Layer Verification Pipeline**

#### Layer 1: Syntax Validation

**Purpose**: Ensure SQL parses correctly for target dialect before execution.

**Implementation**:
```python
import sqlparse
from sqlalchemy import create_engine

def validate_syntax(sql: str, dialect: str) -> ValidationResult:
    # Parse SQL
    try:
        parsed = sqlparse.parse(sql)[0]
    except Exception as e:
        return ValidationResult(valid=False, error=f"Parse error: {e}")
    
    # Check for disallowed statements (DROP, DELETE, TRUNCATE)
    if any(kw in sql.upper() for kw in ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE']):
        return ValidationResult(valid=False, error="Mutation statements not allowed")
    
    # Dialect-specific validation using SQLAlchemy
    engine = create_engine(f"{dialect}://")
    try:
        engine.execute(f"EXPLAIN {sql}")  # Dry run
        return ValidationResult(valid=True)
    except Exception as e:
        return ValidationResult(valid=False, error=f"Dialect error: {e}")
```

**Constraints Applied**:
- No data mutation statements (INSERT, UPDATE, DELETE)
- No schema modification (DROP, ALTER)
- Query timeout limit (30 seconds)

#### Layer 2: Semantic Verification

**Purpose**: Compare generated SQL intent with original NL query to detect logic errors.

**Approach**: LLM-based semantic equivalence checking

```python
def verify_semantics(nl_query: str, generated_sql: str, context: Context) -> SemanticResult:
    verification_prompt = f"""
You are a SQL verification expert. Compare the user's natural language query 
with the generated SQL to determine if they are semantically equivalent.

Natural Language Query: {nl_query}

Generated SQL:
{generated_sql}

Database Schema:
{context.schema}

Check for these common errors:
1. Wrong SELECT columns (e.g., COUNT(*) when average requested)
2. Incorrect JOIN type (INNER vs LEFT/RIGHT)
3. Missing WHERE filters
4. Wrong aggregation function (SUM vs AVG vs COUNT)
5. Incorrect GROUP BY columns
6. Missing ORDER BY when ranking requested

Respond with JSON:
{{
  "semantically_equivalent": true/false,
  "confidence": 0.0-1.0,
  "errors_detected": ["error1", "error2", ...],
  "suggested_fix": "corrected SQL if errors found"
}}
"""
    
    response = llm.generate(verification_prompt)
    return parse_verification_response(response)
```

**Error Pattern Detection** (Rule-based augmentation):

```python
SEMANTIC_ERROR_RULES = [
    {
        "pattern": "COUNT(*)" in sql and "average" in nl_query.lower(),
        "error": "Used COUNT instead of AVG for average calculation",
        "fix": lambda sql: sql.replace("COUNT(*)", "AVG(column_name)")
    },
    {
        "pattern": "INNER JOIN" in sql and "all" in nl_query.lower(),
        "error": "Used INNER JOIN which excludes non-matching rows",
        "fix": lambda sql: sql.replace("INNER JOIN", "LEFT JOIN")
    },
    # ... more rules
]
```

#### Layer 3: Result Sanity Checking

**Purpose**: Detect anomalous results suggesting query errors.

**Checks**:
1. **Negative values in inherently positive metrics** (counts, prices)
2. **Excessive NULL proportion** (>50% of rows)
3. **Outliers beyond reasonable range** (e.g., 1000x standard deviations)
4. **Empty results when data expected** (e.g., querying current year returns nothing)
5. **Duplicate rows** when DISTINCT expected

```python
def sanity_check_results(results: DataFrame, query_intent: Intent) -> SanityResult:
    issues = []
    
    # Check for negative values in count/sum columns
    for col in results.select_dtypes(include=['number']).columns:
        if query_intent.expects_positive(col) and (results[col] < 0).any():
            issues.append(f"Negative values found in {col}")
    
    # Check NULL proportion
    null_ratio = results.isnull().sum() / len(results)
    if (null_ratio > 0.5).any():
        issues.append(f"High NULL proportion in {null_ratio[null_ratio > 0.5].index.tolist()}")
    
    # Check for empty results
    if len(results) == 0 and query_intent.expects_results:
        issues.append("Query returned no results (unexpected)")
    
    # Statistical outlier detection (Z-score > 3)
    for col in results.select_dtypes(include=['number']).columns:
        z_scores = (results[col] - results[col].mean()) / results[col].std()
        if (abs(z_scores) > 3).any():
            issues.append(f"Potential outliers in {col}")
    
    return SanityResult(passed=len(issues)==0, issues=issues)
```

#### Auto-Correction Engine

**When errors detected**:
1. **First attempt**: Regenerate SQL with error-specific constraints in prompt
   ```
   Previous attempt failed because: {error_description}
   Ensure the corrected SQL: {specific_constraint}
   ```

2. **Second attempt**: Use alternative generation strategy (e.g., different few-shot examples)

3. **Third attempt**: Simplify query (remove complex clauses, try basic version)

4. **Failure**: Present error to user with explanation:
   ```
   "I encountered difficulty generating SQL for this query. The issue is: {error}.
   Could you try rephrasing your question or providing more details?"
   ```

**Expected Impact**: 95%+ error detection rate, <5% false positives.

---

### 9.6 Challenge: Result Interpretability

**Problem**: Raw tabular outputs lack visual context for trend identification and pattern recognition.

**IDI Solution**: **Automatic Visualization Selection + Rendering**

#### Component 1: Chart Type Decision Tree

```python
def select_chart_type(results: DataFrame, query_intent: Intent) -> ChartSpec:
    num_rows = len(results)
    num_cols = len(results.columns)
    col_types = results.dtypes
    
    # Single aggregate value (e.g., "What was total revenue?")
    if num_rows == 1 and num_cols == 1:
        return ChartSpec(type="KPI_CARD", config={"large_number": True})
    
    # Time series detection
    if has_datetime_column(results):
        date_col = get_datetime_column(results)
        value_cols = get_numeric_columns(results)
        return ChartSpec(
            type="LINE_CHART",
            x=date_col,
            y=value_cols,
            config={"show_trend_line": True}
        )
    
    # Categorical comparison (≤10 categories)
    if has_categorical_column(results) and num_rows <= 10:
        cat_col = get_categorical_column(results)
        value_col = get_numeric_columns(results)[0]
        return ChartSpec(
            type="BAR_CHART",
            x=cat_col,
            y=value_col,
            config={"orientation": "vertical"}
        )
    
    # Categorical comparison (>10 categories)
    if has_categorical_column(results) and num_rows > 10:
        # Show top 10 + table for rest
        cat_col = get_categorical_column(results)
        value_col = get_numeric_columns(results)[0]
        top_10 = results.nlargest(10, value_col)
        return ChartSpec(
            type="HORIZONTAL_BAR",
            data=top_10,
            x=value_col,
            y=cat_col,
            config={"show_full_table_link": True}
        )
    
    # Proportional breakdown (percentages sum to ~100)
    if is_proportional_data(results):
        cat_col = get_categorical_column(results)
        value_col = get_numeric_columns(results)[0]
        if num_rows <= 6:
            return ChartSpec(type="PIE_CHART", labels=cat_col, values=value_col)
        else:
            return ChartSpec(type="DONUT_CHART", labels=cat_col, values=value_col)
    
    # Two-dimensional comparison (e.g., region × product)
    if num_cols == 3 and len(get_categorical_columns(results)) == 2:
        dim1, dim2 = get_categorical_columns(results)
        value = get_numeric_columns(results)[0]
        return ChartSpec(type="GROUPED_BAR", x=dim1, group=dim2, y=value)
    
    # Default fallback
    return ChartSpec(type="TABLE", config={"interactive": True})
```

#### Component 2: Statistical Overlays

**For time series**:
- **Trend lines**: Linear regression fit
- **Moving averages**: 3-month or 12-month MA
- **Confidence intervals**: ±1 std dev bands

**For distributions**:
- **Quartile markers**: Q1, median, Q3 on histograms
- **Box plots**: For variability visualization
- **Z-score annotations**: Flag outliers

```python
def add_statistical_overlays(chart_spec: ChartSpec, results: DataFrame) -> ChartSpec:
    if chart_spec.type == "LINE_CHART":
        # Add trend line
        from scipy.stats import linregress
        x_numeric = pd.to_numeric(results[chart_spec.x])
        y = results[chart_spec.y]
        slope, intercept, r_value, p_value, std_err = linregress(x_numeric, y)
        
        chart_spec.add_annotation(
            type="trend_line",
            equation=f"y = {slope:.2f}x + {intercept:.2f}",
            r_squared=r_value**2
        )
    
    if chart_spec.type == "HISTOGRAM":
        # Add quartile lines
        q1, median, q3 = results[chart_spec.y].quantile([0.25, 0.5, 0.75])
        chart_spec.add_vertical_lines([
            {"x": q1, "label": "Q1", "color": "blue"},
            {"x": median, "label": "Median", "color": "red"},
            {"x": q3, "label": "Q3", "color": "blue"}
        ])
    
    return chart_spec
```

#### Component 3: Interactive Features

**Drill-down**:
- Click bar/pie slice → filter to that category and regenerate visualization
- Example: Click "Northeast" region → show Northeast sales by product category

**Export**:
- CSV/Excel download with formatted data
- PNG/SVG chart export for presentations
- Copy SQL to clipboard

**Dashboard Composition**:
- "Pin" button to add visualization to personal dashboard
- Arrange multiple pinned charts in grid layout
- Share dashboard link with colleagues

**Expected Impact**: 40-50% improvement in insight comprehension speed vs. raw tables.

---

### 9.7 Challenge: Computational Resource Constraints

**Problem**: State-of-the-art LLMs require extensive GPU resources and API costs.

**IDI Solution**: **Local Deployment with Quantization + Model Selection**

#### Strategy 1: Model Size Optimization

**Target Hardware**: 16GB RAM, 8GB VRAM (NVIDIA RTX 3060/3070 equivalent)

**Model Selection Criteria**:
1. **Parameter count**: ≤13B for primary models (fit in 8GB VRAM with 4-bit quantization)
2. **Performance**: Match or exceed 70B prompted models after fine-tuning
3. **Licensing**: Open-source (Apache 2.0, MIT) for commercial use

**Candidates**:

| Model | Parameters | Quantized Size (4-bit) | Strengths | Use Case |
|-------|-----------|----------------------|-----------|----------|
| Code Llama 13B Instruct | 13B | ~7GB | SQL generation, code understanding | SQL Generator Agent |
| Mistral 7B Instruct v0.2 | 7B | ~4GB | Instruction following, reasoning | Query Understanding + Verification |
| Phi-3 Medium | 14B | ~8GB | Efficient reasoning, small context | Alternative to Mistral |
| DeepSeek Coder 6.7B | 6.7B | ~4GB | Strong SQL performance, fast | Alternative SQL Generator |

**Rationale**: Using two specialized 7-13B models (total ~11GB VRAM) outperforms single 70B model while fitting in hardware constraints.

#### Strategy 2: Quantization

**4-bit Quantization** using GPTQ or bitsandbytes:
- **Memory reduction**: 75% vs. FP16 (13B model: 26GB → 7GB)
- **Accuracy impact**: <2% degradation on benchmarks after fine-tuning
- **Inference speed**: 2-3x faster on consumer GPUs

**Implementation**:
```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,  # Nested quantization for additional compression
    bnb_4bit_quant_type="nf4"  # Normal Float 4-bit
)

model = AutoModelForCausalLM.from_pretrained(
    "codellama/CodeLlama-13b-Instruct-hf",
    quantization_config=quantization_config,
    device_map="auto"  # Automatic GPU/CPU distribution
)
```

#### Strategy 3: Inference Optimization

**Caching**:
- **KV-Cache**: Store key-value activations for repeated prompt prefixes (schema context)
- **Result Cache**: Memoize SQL generation for identical queries

**Batching**:
- Process multiple clarification questions in single forward pass
- Batch verification checks for candidate SQL variants

**Prompt Compression**:
- Remove redundant whitespace/comments from schema
- Use abbreviations for common terms in few-shot examples
- Truncate to maximum context length (2048-4096 tokens)

**CPU Offloading**:
- Keep embeddings and small models (verification) on CPU
- Reserve GPU for heavyweight SQL generation

#### Strategy 4: Fine-Tuning Efficiency

**QLoRA (Quantized Low-Rank Adaptation)**:
- Train only small adapter layers (~0.5% of parameters)
- Reduces training memory 60-70% vs. full fine-tuning
- Enables fine-tuning 13B model on 8GB VRAM

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,  # Rank of adapter matrices
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # Apply to attention layers
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(base_model, lora_config)
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Trainable parameters: {trainable_params / 1e6:.2f}M")  # ~50M for 13B model
```

**Training Data Efficiency**:
- Synthetic generation yields 500-1000 examples vs. manual annotation
- Focus on high-diversity examples (different query types, schema patterns)

**Expected Impact**: <$10 total cloud compute cost for fine-tuning (using free Colab/Kaggle GPU hours).

---

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
- All 6 modules have specified inputs, outputs, and responsibilities
- Metrics defined for accuracy (>90%), latency (<5s), usability (SUS >70)

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

#### Activity 3.3: Verification, Visualization, and Orchestration (Week 11-12)

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
- Implement Multi-Agent Orchestrator
  - LangGraph workflow definition
  - State management
  - Error handling and retry logic
- Develop web interface
  - Keyword-assisted query builder UI
  - Visualization dashboard
  - Clarification dialogue components

**Deliverables**:
- Verification Agent with comprehensive test suite
- Visualization Engine with 5+ chart types supported
- Multi-Agent Orchestrator coordinating all modules
- Functional web interface (React frontend)
- End-to-end integration tests

**Success Criteria**:
- Verification detects >90% of semantic errors with <10% false positives
- Visualization correctly selects chart type for >85% of result sets
- Orchestrator successfully routes queries through appropriate workflow paths
- Web interface loads and processes queries end-to-end

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

**Primary Deliverable**: Functional IDI system with six integrated modules achieving target performance metrics.

**Quantitative Targets**:
- **Execution Accuracy**: 90-95% on domain-specific queries, 85-90% on cross-domain benchmarks
- **Latency**: <5 seconds for 90% of queries
- **Verification Performance**: >95% error detection, <5% false positives
- **Ambiguity Resolution**: >85% success rate, <2 average clarification turns
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

### 14.2 Project Management Risks

**Risk 5: Scope Creep**
- **Probability**: High (50-60%) [common in thesis projects]
- **Impact**: Medium (timeline delays)
- **Mitigation**:
  - Strict prioritization: Core modules first, enhancements only if time permits
  - Weekly progress reviews with advisor to maintain focus
  - Define MVP clearly in Phase 1
- **Contingency**: Cut nice-to-have features (advanced visualizations, dashboard composition)

**Risk 6: Timeline Slippage**
- **Probability**: Medium (35-45%)
- **Impact**: High (missed defense deadline)
- **Mitigation**:
  - Build 1-week buffer between Phases 3 and 4
  - Parallel development where possible (frontend + backend)
  - Early start (before semester begins, as mentioned)
  - Bi-weekly checkpoint meetings
- **Contingency**: Reduce evaluation scope (skip user study, rely on benchmarks + heuristic evaluation)

**Risk 7: Advisor Availability Limited**
- **Probability**: Low (10-20%)
- **Impact**: Medium (feedback delays)
- **Mitigation**:
  - Establish regular meeting schedule early
  - Prepare concise progress reports for efficient reviews
  - Leverage university resources (writing center, peer review)
- **Contingency**: Seek co-advisor or senior PhD student mentorship

### 14.3 External Risks

**Risk 8: Benchmark Dataset Access Issues**
- **Probability**: Low (5-10%)
- **Impact**: Medium (evaluation limitations)
- **Mitigation**:
  - Download datasets early in Phase 1
  - Maintain local backups
  - Have alternative benchmarks identified
- **Contingency**: Use only publicly available benchmarks + custom test set

**Risk 9: User Study Recruitment Failure**
- **Probability**: Medium (30-40%) [especially in academic environment]
- **Impact**: Low (alternative evaluation methods exist)
- **Mitigation**:
  - Recruit early (Week 10-11)
  - Offer incentives (coffee gift cards, lottery for larger prize)
  - Leverage advisor networks (professors, local businesses)
- **Contingency**: Substitute with heuristic evaluation, cognitive walkthrough with peers (fully acceptable for thesis)

**Risk 10: Hardware Failure**
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