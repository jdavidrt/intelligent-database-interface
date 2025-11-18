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

**Problem**: Exploratory data analysis requires conversational sequences with context preservation, progressive refinement, the ability to ask follow-up questions from results, and provide feedback for query adjustment.

**IDI Solution**: **Stateful Conversation Manager with Follow-Up and Feedback Support**

#### Component 1: Dialogue State Machine

```
States:
- INITIAL: Fresh conversation, no context
- CLARIFYING: Awaiting user response to ambiguity questions
- PROCESSING: Query processing in progress (with progress updates)
- RESULTS_READY: Displaying results, ready for follow-up or feedback
- REFINING: Processing user feedback to adjust query
- ERROR: Handling query failure, offering retry
- SAVING_SESSION: User saving conversation context

Transitions:
INITIAL --[query submitted]--> CLARIFYING (if ambiguities) | PROCESSING (if clear)
CLARIFYING --[user response]--> PROCESSING
PROCESSING --[success]--> RESULTS_READY | --[failure]--> ERROR
RESULTS_READY --[follow-up query]--> CLARIFYING | PROCESSING
RESULTS_READY --[feedback]--> REFINING
RESULTS_READY --[save request]--> SAVING_SESSION
REFINING --[adjusted query ready]--> PROCESSING
ERROR --[retry/rephrase]--> CLARIFYING | PROCESSING
SAVING_SESSION --[saved]--> RESULTS_READY (can continue)
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

#### Component 3: Progressive Refinement and Feedback Handling

**Scenario 1: Progressive Narrowing** (User starts broad, narrows iteratively)

```
Turn 1:
User: "Show me sales performance"
System: [Clarifies → Generates query for total sales]
Result: $10.5M total sales in Q3 2024

Turn 2:
User: "By region"  [Follow-up from results]
System: [Infers: GROUP BY region for the same metric and time period]
Result: Northeast $4.2M, Southeast $3.1M, West $2.7M, Midwest $0.5M

Turn 3:
User: "Northeast only, by product category"  [Further drill-down]
System: [Infers: Same metric, Q3 2024, filter region='Northeast', GROUP BY product_category]
Result: Electronics $1.8M, Apparel $1.5M, Home Goods $0.9M
```

**Scenario 2: Feedback-Based Refinement** (User provides adjustment feedback)

```
Turn 1:
User: "Show me top products by revenue"
System: Generates query, shows all products sorted by revenue (200+ results)

Turn 2:
User: "Too many results, show me just the top 10"  [Feedback: limit results]
System: [Detects feedback intent → Adds LIMIT 10 to existing query]
Result: Top 10 products displayed

Turn 3:
User: "Include product categories too"  [Feedback: add column]
System: [Adds product_category to SELECT and GROUP BY]
Result: Top 10 products with categories

Turn 4:
User: "Make it simpler, remove the timestamps"  [Feedback: simplify output]
System: [Removes timestamp columns from SELECT]
Result: Simplified table with product, category, revenue only
```

**Feedback Pattern Detection**:
```python
FEEDBACK_PATTERNS = {
    "too_many": {
        "triggers": ["too many", "limit to", "just top", "only show"],
        "action": "add_limit",
        "examples": ["Show me just top 5", "Too many results"]
    },
    "simplify": {
        "triggers": ["simpler", "remove", "exclude", "don't need"],
        "action": "remove_columns",
        "examples": ["Make it simpler", "Remove the dates"]
    },
    "add_detail": {
        "triggers": ["include", "add", "also show", "with"],
        "action": "add_columns",
        "examples": ["Include categories", "Add timestamps"]
    },
    "change_grouping": {
        "triggers": ["by", "break down", "group by"],
        "action": "modify_groupby",
        "examples": ["By region instead", "Break down by month"]
    },
    "filter_narrow": {
        "triggers": ["only", "just", "filter to", "excluding"],
        "action": "add_where_clause",
        "examples": ["Only Q3", "Excluding refunds"]
    }
}
```

**Implementation**:
- Maintain modification stack, applying deltas to base query rather than regenerating from scratch
- Detect feedback intent using pattern matching + LLM classification
- Apply incremental modifications to previous SQL
- Preserve conversation context (all previous queries and results)

#### Component 4: Result Caching

**Strategy**: Cache query results for session duration
- **Key**: Query fingerprint (canonicalized SQL + parameters)
- **Value**: Result DataFrame + metadata (execution time, row count)
- **Eviction**: LRU policy with 100MB session limit

**Benefit**: Sub-second response for repeated/similar queries

**Expected Impact**:
- 90% success rate for 3+ turn conversations
- 85% accuracy in detecting follow-up intent vs. new query
- 80% success rate in applying feedback correctly (limited modifications)
- Average 3-5 turns per investigative workflow

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

### 9.7 Challenge: Computational Resource Constraints and Extended Processing Times

**Problem**: State-of-the-art LLMs require extensive GPU resources and API costs. Additionally, complex queries on resource-constrained devices may require extended processing times, necessitating transparent progress communication and user control.

**IDI Solution**: **Local Deployment with Quantization + Model Selection + Progress Communication**

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

#### Strategy 5: Progress Communication and Timeout Management

**Philosophy**: Trade speed for accessibility—accept up to 30-second processing times to enable deployment on consumer hardware while maintaining user trust through transparent communication.

**Progress Tracking System**:

```python
class ProgressTracker:
    """Tracks query processing progress and estimates completion time."""

    PROCESSING_PHASES = {
        "understanding": {"weight": 0.15, "message": "Analyzing your question..."},
        "context_retrieval": {"weight": 0.10, "message": "Gathering relevant database information..."},
        "sql_generation": {"weight": 0.40, "message": "Crafting your query..."},
        "verification": {"weight": 0.15, "message": "Verifying query correctness..."},
        "execution": {"weight": 0.15, "message": "Executing and retrieving results..."},
        "visualization": {"weight": 0.05, "message": "Creating visualization..."}
    }

    def estimate_completion_time(self, query_complexity: QueryComplexity) -> float:
        """Estimate time based on query complexity and historical data."""
        base_times = {
            QueryComplexity.SIMPLE: 3.0,      # Single table, basic aggregation
            QueryComplexity.MODERATE: 8.0,    # Multiple tables, joins
            QueryComplexity.COMPLEX: 18.0     # Complex joins, nested queries
        }
        return base_times.get(query_complexity, 10.0)

    def update_progress(self, phase: str, percent_complete: float):
        """Emit progress update to frontend."""
        emit_websocket_event({
            "type": "progress_update",
            "phase": phase,
            "message": self.PROCESSING_PHASES[phase]["message"],
            "percent": percent_complete,
            "estimated_remaining": self.estimate_remaining_time()
        })
```

**Creative Status Messages** (displayed during processing):
- "Analyzing your question..."
- "Gathering relevant database information..."
- "Crafting your query... (Estimated: 8 seconds)"
- "Constructing SQL logic..." [████████░░░░] 60%
- "Optimizing join strategy..."
- "Analyzing multi-table relationships..."
- "Verifying query correctness..."
- "Executing and retrieving results..."
- "Creating visualization..."

**Timeout Management**:
```python
class QueryExecutor:
    MAX_TIMEOUT = 30  # seconds

    def execute_with_timeout(self, query_fn, timeout: float = 30):
        """Execute query with cancellation support."""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Query exceeded {timeout}s timeout")

        # Set signal alarm
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = query_fn()
            signal.alarm(0)  # Cancel alarm
            return result
        except TimeoutError:
            return {
                "error": "Query processing exceeded time limit",
                "suggestion": "Try simplifying your query or filtering the data"
            }
```

**User Cancellation Support**:
```python
class CancellableTask:
    """Allows users to cancel long-running queries."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.cancelled = False

    def check_cancellation(self):
        """Check if user cancelled via WebSocket message."""
        if self.cancelled:
            raise TaskCancelledException("User cancelled query")

    def execute_cancellable(self, llm_generation_fn):
        """Execute LLM generation with periodic cancellation checks."""
        # For streaming generation, check cancellation between tokens
        for token in llm_generation_fn(stream=True):
            self.check_cancellation()
            yield token
```

**WebSocket-Based Real-Time Updates**:
```python
# Backend (FastAPI)
from fastapi import WebSocket

@app.websocket("/ws/query/{session_id}")
async def query_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    try:
        # Receive query
        query_data = await websocket.receive_json()

        # Process with progress updates
        async for progress in process_query_streaming(query_data):
            await websocket.send_json({
                "type": "progress",
                "data": progress
            })

        # Send final result
        await websocket.send_json({
            "type": "result",
            "data": final_results
        })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

**Expected Impact**:
- User tolerance for wait times improves from <5s to <25s when progress visible
- Cancellation usage: ~5-10% of complex queries (user realizes query too broad)
- System enables deployment on 80%+ of existing organizational hardware (vs. requiring specialized infrastructure)

---

### 9.8 Challenge: Investigation Continuity

**Problem**: Complex analytical investigations span multiple sessions and require preserving entire investigative contexts (query sequences, intermediate results, conversational threads) for resumption, sharing, or replication—functionality missing from stateless query systems.

**IDI Solution**: **Session Manager with Full Context Persistence**

#### Component 1: Session Persistence Layer

**Session Data Model**:
```python
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
import uuid

@dataclass
class QueryRecord:
    """Single query within a session."""
    query_id: str
    natural_language: str
    generated_sql: str
    execution_time: float
    result_rows: int
    timestamp: datetime
    clarifications: List[Dict[str, Any]]  # Questions and user responses

@dataclass
class Session:
    """Complete investigation session."""
    session_id: str
    name: str  # User-provided
    description: str  # Optional user-provided
    tags: List[str]  # User-provided for organization
    created_at: datetime
    updated_at: datetime
    queries: List[QueryRecord]  # Chronological order
    conversation_history: List[Dict[str, Any]]  # Full dialogue
    results_snapshots: Dict[str, Any]  # Query results (may be truncated for large datasets)

    def save_to_db(self, db_session):
        """Persist session to database."""
        session_data = {
            "session_id": self.session_id,
            "name": self.name,
            "description": self.description,
            "tags": json.dumps(self.tags),
            "created_at": self.created_at,
            "updated_at": datetime.now(),
            "data": json.dumps({
                "queries": [asdict(q) for q in self.queries],
                "conversation": self.conversation_history,
                "results": self.results_snapshots
            })
        }
        db_session.execute(insert_or_update_query, session_data)
```

**Storage Schema** (PostgreSQL with JSONB):
```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],  -- Array of tags
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL,  -- Flexible storage for queries, conversation, results

    -- Indexes for fast retrieval
    CONSTRAINT session_name_unique UNIQUE(name)
);

-- Full-text search on names, descriptions, tags
CREATE INDEX sessions_search_idx ON sessions
USING GIN (to_tsvector('english', name || ' ' || description || ' ' || array_to_string(tags, ' ')));

-- Index on tags for filtering
CREATE INDEX sessions_tags_idx ON sessions USING GIN (tags);

-- Index on timestamps for sorting
CREATE INDEX sessions_created_idx ON sessions (created_at DESC);
```

#### Component 2: Session Management Operations

**Save Session** (User-initiated):
```python
async def save_session(current_context: ConversationContext, metadata: SessionMetadata):
    """Save current conversation as named session."""
    session = Session(
        session_id=str(uuid.uuid4()),
        name=metadata.name,
        description=metadata.description,
        tags=metadata.tags,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        queries=[create_query_record(q) for q in current_context.queries],
        conversation_history=current_context.messages,
        results_snapshots=truncate_large_results(current_context.results)
    )

    session.save_to_db(db)
    return {"session_id": session.session_id, "message": "Session saved successfully!"}
```

**Load Session**:
```python
async def load_session(session_id: str) -> ConversationContext:
    """Restore full conversation context from saved session."""
    session = db.query(Session).filter_by(session_id=session_id).first()

    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")

    # Restore conversation context
    context = ConversationContext(
        session_id=session.session_id,
        queries=session.data['queries'],
        messages=session.data['conversation'],
        results=session.data['results']
    )

    return context
```

**List Sessions** (with search/filter):
```python
async def list_sessions(
    search_query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0
) -> List[SessionSummary]:
    """List saved sessions with optional filtering."""
    query = db.query(Session)

    if search_query:
        # Full-text search
        query = query.filter(
            "to_tsvector('english', name || ' ' || description) @@ plainto_tsquery(:search)",
            search=search_query
        )

    if tags:
        # Filter by tags (AND logic: must have all tags)
        query = query.filter(Session.tags.contains(tags))

    sessions = query.order_by(Session.updated_at.desc()).limit(limit).offset(offset).all()

    return [SessionSummary(
        session_id=s.session_id,
        name=s.name,
        description=s.description,
        tags=s.tags,
        query_count=len(s.data['queries']),
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in sessions]
```

**Export Session**:
```python
async def export_session(session_id: str, format: str = "json") -> bytes:
    """Export session for sharing or backup."""
    session = load_session_from_db(session_id)

    if format == "json":
        return json.dumps(asdict(session), indent=2, default=str).encode()

    elif format == "pdf":
        # Generate PDF report with queries, results, visualizations
        return generate_pdf_report(session)

    elif format == "markdown":
        # Generate markdown document
        return generate_markdown_report(session)
```

#### Component 3: Session UI Components

**Session Save Dialog**:
```typescript
interface SessionSaveDialogProps {
  currentContext: ConversationContext;
  onSave: (metadata: SessionMetadata) => void;
}

function SessionSaveDialog({ currentContext, onSave }: SessionSaveDialogProps) {
  return (
    <Dialog>
      <DialogTitle>Save Session</DialogTitle>
      <DialogContent>
        <TextField
          label="Session Name"
          required
          placeholder="Q3 2024 Sales Regional Analysis"
        />
        <TextField
          label="Description (optional)"
          multiline
          placeholder="Investigating August peak performance..."
        />
        <TagInput
          label="Tags"
          placeholder="sales, Q3, regional, 2024"
        />
        <Typography variant="caption">
          This will save {currentContext.queries.length} queries and all conversation history
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={onSave} variant="contained">Save Session</Button>
      </DialogActions>
    </Dialog>
  );
}
```

**Session Library** (Browse saved sessions):
```typescript
function SessionLibrary() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  return (
    <div className="session-library">
      <SearchBar placeholder="Search sessions..." />
      <TagFilter tags={["sales", "Q3", "regional", "2024", ...]} />

      <SessionGrid>
        {sessions.map(session => (
          <SessionCard key={session.session_id}>
            <CardHeader>
              <h3>{session.name}</h3>
              <Chip>{session.query_count} queries</Chip>
            </CardHeader>
            <CardContent>
              <p>{session.description}</p>
              <Tags>{session.tags.map(tag => <Tag>{tag}</Tag>)}</Tags>
              <Timestamp>Last updated: {session.updated_at}</Timestamp>
            </CardContent>
            <CardActions>
              <Button onClick={() => loadSession(session.session_id)}>
                Resume
              </Button>
              <Button onClick={() => exportSession(session.session_id)}>
                Export
              </Button>
              <Button onClick={() => shareSession(session.session_id)}>
                Share
              </Button>
            </CardActions>
          </SessionCard>
        ))}
      </SessionGrid>
    </div>
  );
}
```

**Expected Impact**:
- 40-60% of investigations span multiple work sessions (hours/days apart)
- Saved sessions reduce re-work by 70% (no need to recreate query sequences)
- Knowledge sharing: 30% of sessions exported or shared with colleagues
- Session library becomes organizational knowledge base of common analyses

---
