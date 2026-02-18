# IDI Technology Deep Dive: The Hidden Foundations

*"Before the cathedral rises, one must understand the stone."*

This document explores six critical technologies that form the invisible architecture of your IDI system. Each section answers: **What is it?**, **Why does it matter for IDI?**, **How does it compare to alternatives?**, and **Practical implementation guidance**.

---

## Table of Contents

1. [Vector Database: ChromaDB](#1-vector-database-chromadb)
2. [Session Storage: SQLite vs PostgreSQL](#2-session-storage-sqlite-vs-postgresql)
3. [Visualization Library: Recharts](#3-visualization-library-recharts)
4. [Training Datasets](#4-training-datasets)
5. [WebSockets: Real-Time Progress Updates](#5-websockets-real-time-progress-updates)
6. [Model Format: GGUF](#6-model-format-gguf)
7. [Technology Decision Matrix](#7-technology-decision-matrix)

---

## 1. Vector Database: ChromaDB

### 1.1 What Is It?

A **vector database** stores data as high-dimensional numerical vectors (embeddings) rather than traditional rows and columns. When you convert text into an embedding, you transform its *meaning* into a list of numbers (e.g., 768 floats). Similar meanings produce similar vectors, enabling **semantic search**.

**ChromaDB** is an open-source, embeddable vector database designed specifically for AI applications. It runs in-process (no separate server needed) and integrates seamlessly with Python.

### 1.2 The Difference: Markdown Files vs. Vector Database

| Approach | How It Works | Limitations |
|----------|--------------|-------------|
| **Markdown Files** | You manually paste relevant context into the prompt | Limited by context window size; no automatic relevance filtering; scales poorly |
| **Vector Database** | System automatically finds the most semantically relevant chunks | Scales to millions of documents; finds relevant context even with different wording |

**Example Scenario:**

Your IDI system needs to understand that "revenue" means `total_amount` in the `orders` table.

**With Markdown Files:**
```
You include ALL your documentation in every prompt:
- Business glossary (5,000 tokens)
- Schema documentation (3,000 tokens)
- Example queries (2,000 tokens)
Total: 10,000 tokens consumed EVERY query, even when irrelevant
```

**With ChromaDB:**
```
User asks: "What was our revenue last quarter?"

1. System embeds the question → [0.23, -0.15, 0.87, ...]
2. ChromaDB finds semantically similar stored chunks
3. Returns: "revenue = total_amount in orders table"
4. Only relevant context (200 tokens) added to prompt
```

### 1.3 How ChromaDB Works for IDI

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT ACQUISITION                       │
│  (One-time setup during onboarding)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Business Glossary ──┐                                       │
│  Schema Docs ────────┼──→ Chunking ──→ Embedding ──→ ChromaDB│
│  Example Queries ────┘    (split)      (vectorize)   (store) │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    QUERY TIME (Every query)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Question: "Show me sales by region"                    │
│        │                                                     │
│        ▼                                                     │
│  Embed Question ──→ ChromaDB Similarity Search               │
│        │                    │                                │
│        │                    ▼                                │
│        │           Returns top-3 relevant chunks:            │
│        │           • "sales = SUM(total_amount)..."          │
│        │           • "regions table joins via region_id..."  │
│        │           • "Example: SELECT r.name, SUM(o.total)...│
│        │                                                     │
│        ▼                                                     │
│  Build Prompt = Question + Retrieved Context                 │
│        │                                                     │
│        ▼                                                     │
│  Send to LLM (only ~500 tokens of context, not 10,000)       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Practical Implementation

```python
# Installation
# pip install chromadb sentence-transformers

import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB (persisted to disk)
client = chromadb.PersistentClient(path="./chroma_data")

# Create a collection for your domain context
collection = client.get_or_create_collection(
    name="idi_context",
    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
)

# Initialize embedding model (runs locally, ~90MB)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# ============ ONBOARDING: Store your context ============

context_documents = [
    {
        "id": "glossary_revenue",
        "text": "Revenue refers to total_amount column in the orders table. "
                "It represents the final sale price including tax.",
        "metadata": {"type": "glossary", "entity": "revenue"}
    },
    {
        "id": "schema_orders",
        "text": "Table: orders. Columns: order_id (PK), customer_id (FK), "
                "order_date (DATE), total_amount (DECIMAL). "
                "Joins to customers via customer_id.",
        "metadata": {"type": "schema", "table": "orders"}
    },
    {
        "id": "example_quarterly_sales",
        "text": "Question: What were Q3 sales? "
                "SQL: SELECT SUM(total_amount) FROM orders "
                "WHERE order_date BETWEEN '2024-07-01' AND '2024-09-30'",
        "metadata": {"type": "example", "complexity": "simple"}
    }
]

# Add documents to collection
for doc in context_documents:
    embedding = embedding_model.encode(doc["text"]).tolist()
    collection.add(
        ids=[doc["id"]],
        embeddings=[embedding],
        documents=[doc["text"]],
        metadatas=[doc["metadata"]]
    )

# ============ QUERY TIME: Retrieve relevant context ============

def get_relevant_context(user_question: str, top_k: int = 3) -> list[str]:
    """Retrieve most relevant context for a user question."""
    question_embedding = embedding_model.encode(user_question).tolist()
    
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    # Results sorted by relevance (smallest distance = most similar)
    return results["documents"][0]  # List of relevant text chunks


# Example usage
question = "What was our revenue last quarter?"
context_chunks = get_relevant_context(question)

print("Retrieved context:")
for i, chunk in enumerate(context_chunks, 1):
    print(f"  {i}. {chunk[:100]}...")

# Build prompt with retrieved context
prompt = f"""
Given this database context:
{chr(10).join(context_chunks)}

User question: {question}

Generate the SQL query:
"""
```

### 1.5 ChromaDB vs Alternatives

| Feature | ChromaDB | FAISS | Pinecone | Weaviate |
|---------|----------|-------|----------|----------|
| **Deployment** | Embedded (in-process) | Library | Cloud-hosted | Server/Cloud |
| **Setup Complexity** | Very Low | Low | Medium | Medium |
| **Cost** | Free | Free | Paid | Free/Paid |
| **Best For** | Local apps, prototypes | Large-scale search | Production SaaS | Enterprise |
| **IDI Fit** | ✅ **Perfect** | Good | Overkill | Overkill |

**Recommendation for IDI:** ChromaDB is ideal because it:
- Runs entirely locally (no cloud costs, no network latency)
- Persists to disk (survives restarts)
- Simple Python API
- Sufficient for thousands of context documents

---

## 2. Session Storage: SQLite vs PostgreSQL

### 2.1 The Decision Framework

Your IDI system needs to store:
- **Session metadata**: name, description, tags, timestamps
- **Query history**: user questions, generated SQL, execution results
- **Conversation threads**: multi-turn dialogue context

### 2.2 Comparison

| Aspect | SQLite | PostgreSQL |
|--------|--------|------------|
| **Setup** | Zero config (single file) | Requires server installation |
| **Concurrency** | Single writer at a time | Many concurrent writers |
| **JSON Support** | Basic (`json_extract`) | Advanced (JSONB with indexing) |
| **Full-Text Search** | FTS5 extension (good) | Built-in (excellent) |
| **Performance** | Excellent for read-heavy | Excellent for write-heavy |
| **Deployment** | File-based, portable | Client-server architecture |
| **IDI Dev Phase** | ✅ **Perfect** | Overkill |
| **IDI Production** | Limited | ✅ **Recommended** |

### 2.3 Practical Recommendation

**Use SQLite for development**, PostgreSQL only if you need:
- Multiple simultaneous users
- Complex JSONB queries
- Production deployment with high write volume

```python
# SQLite implementation for IDI sessions
import sqlite3
import json
from datetime import datetime
from uuid import uuid4

def init_session_db(db_path: str = "idi_sessions.db"):
    """Initialize SQLite database for session storage."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            tags TEXT,  -- JSON array stored as text
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            data TEXT NOT NULL  -- JSON blob for queries, conversation, results
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_updated 
        ON sessions(updated_at DESC)
    """)
    conn.commit()
    return conn


def save_session(conn, name: str, description: str, tags: list, 
                 queries: list, conversation: list, results: list) -> str:
    """Save a new session or update existing."""
    session_id = str(uuid4())
    now = datetime.now().isoformat()
    
    data = json.dumps({
        "queries": queries,
        "conversation": conversation,
        "results": results
    })
    
    conn.execute("""
        INSERT INTO sessions (session_id, name, description, tags, 
                              created_at, updated_at, data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, name, description, json.dumps(tags), now, now, data))
    conn.commit()
    
    return session_id


def load_session(conn, session_id: str) -> dict:
    """Load a session by ID."""
    cursor = conn.execute("""
        SELECT name, description, tags, created_at, updated_at, data
        FROM sessions WHERE session_id = ?
    """, (session_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        "session_id": session_id,
        "name": row[0],
        "description": row[1],
        "tags": json.loads(row[2]),
        "created_at": row[3],
        "updated_at": row[4],
        **json.loads(row[5])  # queries, conversation, results
    }


def search_sessions(conn, query: str) -> list:
    """Simple search by name/description."""
    cursor = conn.execute("""
        SELECT session_id, name, description, tags, updated_at
        FROM sessions
        WHERE name LIKE ? OR description LIKE ?
        ORDER BY updated_at DESC
        LIMIT 20
    """, (f"%{query}%", f"%{query}%"))
    
    return [
        {
            "session_id": row[0],
            "name": row[1],
            "description": row[2],
            "tags": json.loads(row[3]),
            "updated_at": row[4]
        }
        for row in cursor.fetchall()
    ]
```

### 2.4 Compatibility with Training Datasets

Both SQLite and PostgreSQL can work with your training datasets. The datasets (Spider, BIRD, gretelai) typically come as:
- JSON files (load into any DB)
- SQLite databases (Spider uses SQLite for its example DBs)

**Spider's databases ARE SQLite files**, so using SQLite for development gives you direct compatibility for testing.

---

## 3. Visualization Library: Recharts

### 3.1 Why Recharts for IDI?

Recharts is built specifically for React applications, using a **declarative, component-based** approach that mirrors how React itself works.

### 3.2 Comparison Matrix

| Library | React Integration | Learning Curve | Bundle Size | Chart Types | IDI Fit |
|---------|-------------------|----------------|-------------|-------------|---------|
| **Recharts** | Native (components) | Low | ~150KB | 12+ basic | ✅ **Best** |
| **Chart.js** | Via wrapper | Low | ~65KB | 8 basic | Good |
| **Plotly.js** | Via wrapper | Medium | ~3MB | 40+ advanced | Overkill |
| **D3.js** | Manual | High | ~250KB | Unlimited | Too complex |
| **ECharts** | Via wrapper | Medium | ~800KB | 20+ advanced | Good |

### 3.3 Why Recharts Wins for IDI

1. **React-Native Components**: No wrapper libraries needed
2. **Responsive by Default**: Charts automatically resize
3. **Sufficient Chart Types**: Line, Bar, Pie, Area, Scatter—all you need for SQL results
4. **Professional Appearance**: Clean, modern default styling
5. **TypeScript Support**: Full type definitions included

### 3.4 Practical Implementation

```tsx
// Installation: npm install recharts

import React from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell
} from 'recharts';

// Types for SQL query results
interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  metadata: {
    hasDateColumn: boolean;
    hasCategoricalColumn: boolean;
    numericColumns: string[];
  };
}

// Automatic chart type selection based on data structure
function selectChartType(result: QueryResult): 'line' | 'bar' | 'pie' | 'table' {
  const { rows, metadata } = result;
  
  // Time series → Line chart
  if (metadata.hasDateColumn && metadata.numericColumns.length >= 1) {
    return 'line';
  }
  
  // Categorical with numeric → Bar chart (if ≤10 categories)
  if (metadata.hasCategoricalColumn && rows.length <= 10) {
    return 'bar';
  }
  
  // Proportional data (percentages) → Pie chart
  if (rows.length <= 6 && metadata.numericColumns.length === 1) {
    return 'pie';
  }
  
  // Default → Table
  return 'table';
}

// Example: Sales by Region Bar Chart
interface SalesData {
  region: string;
  sales: number;
}

const SalesByRegionChart: React.FC<{ data: SalesData[] }> = ({ data }) => {
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];
  
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="region" />
        <YAxis 
          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
        />
        <Tooltip 
          formatter={(value: number) => [`$${value.toLocaleString()}`, 'Sales']}
        />
        <Legend />
        <Bar dataKey="sales" fill="#8884d8">
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

// Example: Monthly Trend Line Chart
interface TrendData {
  month: string;
  revenue: number;
  orders: number;
}

const MonthlyTrendChart: React.FC<{ data: TrendData[] }> = ({ data }) => (
  <ResponsiveContainer width="100%" height={400}>
    <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="month" />
      <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
      <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
      <Tooltip />
      <Legend />
      <Line 
        yAxisId="left"
        type="monotone" 
        dataKey="revenue" 
        stroke="#8884d8" 
        strokeWidth={2}
        dot={{ r: 4 }}
        activeDot={{ r: 6 }}
      />
      <Line 
        yAxisId="right"
        type="monotone" 
        dataKey="orders" 
        stroke="#82ca9d"
        strokeWidth={2}
      />
    </LineChart>
  </ResponsiveContainer>
);

// Example: Category Distribution Pie Chart
interface CategoryData {
  name: string;
  value: number;
}

const CategoryPieChart: React.FC<{ data: CategoryData[] }> = ({ data }) => {
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#FF6B6B'];
  
  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={true}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={150}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(value: number) => value.toLocaleString()} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

export { SalesByRegionChart, MonthlyTrendChart, CategoryPieChart, selectChartType };
```

---

## 4. Training Datasets

### 4.1 Dataset Landscape for NL2SQL

| Dataset | Size | License | Best For | Quality |
|---------|------|---------|----------|---------|
| **gretelai/synthetic_text_to_sql** | 105K samples | Apache 2.0 | Training SQL generation | ⭐⭐⭐⭐⭐ |
| **b-mc2/sql-create-context** | 78K samples | CC BY-SA 4.0 | Training with schema context | ⭐⭐⭐⭐ |
| **Spider** | 10K samples | CC BY-SA 4.0 | Evaluation benchmark | ⭐⭐⭐⭐⭐ |
| **BIRD** | 12K samples | CC BY-NC 4.0 | Complex enterprise scenarios | ⭐⭐⭐⭐⭐ |
| **WikiSQL** | 80K samples | BSD | Simple single-table queries | ⭐⭐⭐ |
| **SynSQL-2.5M** | 2.5M samples | Apache 2.0 | Large-scale training (NEW 2025) | ⭐⭐⭐⭐ |

### 4.2 Recommended Dataset Strategy for IDI

```
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PRIMARY: gretelai/synthetic_text_to_sql (15-20K samples)    │
│  ├── Largest diverse synthetic dataset                       │
│  ├── Apache 2.0 license (commercial-friendly)                │
│  ├── Multiple complexity levels                              │
│  └── Schema context included                                 │
│                                                              │
│  SUPPLEMENTARY: b-mc2/sql-create-context (5-10K samples)     │
│  ├── Additional variety in phrasing                          │
│  └── Good schema-to-SQL mappings                             │
│                                                              │
│  VALIDATION: Spider dev set (1,034 samples)                  │
│  └── Industry-standard benchmark for accuracy measurement    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Dataset Structure Comparison

**gretelai/synthetic_text_to_sql:**
```json
{
  "id": "example_001",
  "domain": "retail",
  "sql_complexity": "subquery",
  "sql_task_type": "analytics",
  "sql_prompt": "Show me the top 5 customers by total purchase amount",
  "sql_context": "CREATE TABLE customers (id INT, name VARCHAR); CREATE TABLE orders (id INT, customer_id INT, amount DECIMAL);",
  "sql": "SELECT c.name, SUM(o.amount) as total FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.name ORDER BY total DESC LIMIT 5",
  "sql_explanation": "This query joins customers with their orders, calculates total purchase amounts, and returns the top 5."
}
```

**b-mc2/sql-create-context:**
```json
{
  "question": "What is the average price of products in the Electronics category?",
  "context": "CREATE TABLE products (id INT PRIMARY KEY, name VARCHAR(100), category VARCHAR(50), price DECIMAL(10,2));",
  "answer": "SELECT AVG(price) FROM products WHERE category = 'Electronics'"
}
```

### 4.4 Data Preparation Script

```python
# data_preparation.py
# Prepare training data for IDI LoRA fine-tuning

from datasets import load_dataset
import json

def prepare_gretel_dataset(num_samples: int = 15000) -> list[dict]:
    """Load and format gretelai dataset for training."""
    
    ds = load_dataset("gretelai/synthetic_text_to_sql", split="train")
    
    # Filter for quality and diversity
    samples = []
    complexity_counts = {"single join": 0, "multiple joins": 0, "subquery": 0, "aggregation": 0}
    
    for item in ds:
        complexity = item.get("sql_complexity", "simple")
        
        # Balance complexity levels
        if complexity_counts.get(complexity, 0) >= num_samples // 4:
            continue
        
        # Format for training
        formatted = {
            "instruction": f"Given this database schema:\n{item['sql_context']}\n\nGenerate SQL for: {item['sql_prompt']}",
            "input": "",
            "output": item['sql']
        }
        
        samples.append(formatted)
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        if len(samples) >= num_samples:
            break
    
    return samples


def prepare_spider_validation() -> list[dict]:
    """Load Spider dev set for validation."""
    
    ds = load_dataset("spider", split="validation")
    
    samples = []
    for item in ds:
        formatted = {
            "instruction": f"Database: {item['db_id']}\nQuestion: {item['question']}",
            "input": "",
            "output": item['query'],
            "db_id": item['db_id']  # Keep for execution testing
        }
        samples.append(formatted)
    
    return samples


def save_datasets():
    """Save prepared datasets to JSON files."""
    
    print("Preparing gretelai training data...")
    train_data = prepare_gretel_dataset(15000)
    
    print("Preparing Spider validation data...")
    val_data = prepare_spider_validation()
    
    with open("train_sql_generator.json", "w") as f:
        json.dump(train_data, f, indent=2)
    
    with open("val_spider.json", "w") as f:
        json.dump(val_data, f, indent=2)
    
    print(f"Saved {len(train_data)} training samples")
    print(f"Saved {len(val_data)} validation samples")


if __name__ == "__main__":
    save_datasets()
```

### 4.5 Additional Dataset Recommendations

For your **Query Understanding Agent** (intent classification, entity extraction):

| Dataset | Purpose | Link |
|---------|---------|------|
| **ATIS** | Intent classification for queries | Classic NLU benchmark |
| **SNIPS** | Slot filling and intent | Good for entity extraction |
| **Custom synthetic** | Generate from your own templates | Most relevant for IDI |

For your **Verification Agent** (error detection):

| Dataset | Purpose | Notes |
|---------|---------|-------|
| **NL2SQL-BUGs** | Semantic error detection | NEW 2025, 2K annotated errors |
| **Spider with errors** | Synthetic error injection | Create by mutating Spider queries |

---

## 5. WebSockets: Real-Time Progress Updates

### 5.1 Why WebSockets for IDI?

Traditional HTTP requests follow a simple pattern: request → wait → response. But when your LLM takes 5-15 seconds to generate SQL, users stare at a blank screen wondering if anything is happening.

**WebSockets** establish a persistent, bidirectional connection between browser and server. The server can push updates to the client at any time—perfect for:

- Progress indicators during SQL generation
- Streaming token-by-token responses
- Query cancellation (client → server)
- Real-time status updates

### 5.2 HTTP vs WebSocket Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADITIONAL HTTP                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Client                              Server                  │
│    │                                   │                     │
│    │──── POST /query ─────────────────>│                     │
│    │                                   │                     │
│    │         (waiting 10 seconds)      │ Processing...       │
│    │                                   │                     │
│    │<──────────── Response ────────────│                     │
│    │                                   │                     │
│  User sees: Loading spinner for 10s, then sudden result     │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    WEBSOCKET                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Client                              Server                  │
│    │                                   │                     │
│    │════ WebSocket Connection ════════>│                     │
│    │                                   │                     │
│    │──── {type: "query", ...} ────────>│                     │
│    │                                   │                     │
│    │<─── {progress: 10%, phase: "understanding"} ───        │
│    │                                   │                     │
│    │<─── {progress: 40%, phase: "generating SQL"} ──        │
│    │                                   │                     │
│    │<─── {progress: 70%, phase: "verifying"} ───────        │
│    │                                   │                     │
│    │<─── {progress: 90%, phase: "executing"} ───────        │
│    │                                   │                     │
│    │<─── {type: "result", data: {...}} ─────────────        │
│    │                                   │                     │
│  User sees: Live progress bar updating every second         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 FastAPI WebSocket Implementation

```python
# backend/app/api/routes/websocket.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import asyncio
import json

app = FastAPI()

# Track active connections
active_connections: Dict[str, WebSocket] = {}


class ProgressTracker:
    """Track and broadcast query processing progress."""
    
    PHASES = {
        "understanding": {"weight": 0.15, "message": "Analyzing your question..."},
        "context": {"weight": 0.10, "message": "Gathering database context..."},
        "generating": {"weight": 0.40, "message": "Generating SQL query..."},
        "verifying": {"weight": 0.20, "message": "Verifying query correctness..."},
        "executing": {"weight": 0.10, "message": "Executing and fetching results..."},
        "visualizing": {"weight": 0.05, "message": "Creating visualization..."}
    }
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.current_progress = 0
        self.cancelled = False
    
    async def update(self, phase: str, phase_progress: float = 1.0):
        """Send progress update to client."""
        if self.cancelled:
            raise asyncio.CancelledError("Query cancelled by user")
        
        phase_info = self.PHASES.get(phase, {"weight": 0.1, "message": phase})
        
        # Calculate cumulative progress
        phases_list = list(self.PHASES.keys())
        phase_index = phases_list.index(phase) if phase in phases_list else 0
        
        base_progress = sum(
            self.PHASES[p]["weight"] for p in phases_list[:phase_index]
        ) * 100
        
        current_phase_progress = phase_info["weight"] * phase_progress * 100
        total_progress = base_progress + current_phase_progress
        
        await self.websocket.send_json({
            "type": "progress",
            "phase": phase,
            "message": phase_info["message"],
            "progress": round(total_progress, 1),
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def cancel(self):
        """Mark query as cancelled."""
        self.cancelled = True


@app.websocket("/ws/query/{session_id}")
async def query_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for query processing with progress updates."""
    
    await websocket.accept()
    active_connections[session_id] = websocket
    
    tracker = ProgressTracker(session_id, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "query":
                # Process query with progress updates
                try:
                    result = await process_query_with_progress(
                        data["query"],
                        data.get("keywords", []),
                        tracker
                    )
                    
                    await websocket.send_json({
                        "type": "result",
                        "success": True,
                        "data": result
                    })
                    
                except asyncio.CancelledError:
                    await websocket.send_json({
                        "type": "cancelled",
                        "message": "Query cancelled by user"
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data["type"] == "cancel":
                tracker.cancel()
                await websocket.send_json({
                    "type": "cancelled",
                    "message": "Cancellation requested"
                })
    
    except WebSocketDisconnect:
        pass
    finally:
        del active_connections[session_id]


async def process_query_with_progress(
    query: str, 
    keywords: list, 
    tracker: ProgressTracker
) -> dict:
    """Process query with progress updates at each phase."""
    
    # Phase 1: Query Understanding
    await tracker.update("understanding", 0.0)
    intent = await understand_query(query, keywords)
    await tracker.update("understanding", 1.0)
    
    # Phase 2: Context Retrieval
    await tracker.update("context", 0.0)
    context = await get_relevant_context(query)
    await tracker.update("context", 1.0)
    
    # Phase 3: SQL Generation (longest phase)
    await tracker.update("generating", 0.0)
    
    # Simulate streaming progress during generation
    sql = ""
    async for token in generate_sql_streaming(intent, context):
        sql += token
        # Update progress based on estimated completion
        progress = min(len(sql) / 200, 0.9)  # Estimate 200 chars avg
        await tracker.update("generating", progress)
    
    await tracker.update("generating", 1.0)
    
    # Phase 4: Verification
    await tracker.update("verifying", 0.0)
    verification = await verify_sql(sql, query)
    await tracker.update("verifying", 1.0)
    
    # Phase 5: Execution
    await tracker.update("executing", 0.0)
    results = await execute_sql(sql)
    await tracker.update("executing", 1.0)
    
    # Phase 6: Visualization
    await tracker.update("visualizing", 0.0)
    chart_spec = determine_visualization(results)
    await tracker.update("visualizing", 1.0)
    
    return {
        "sql": sql,
        "results": results,
        "visualization": chart_spec,
        "verification": verification
    }
```

### 5.4 React Frontend WebSocket Hook

```tsx
// frontend/src/hooks/useQueryWebSocket.ts

import { useState, useEffect, useRef, useCallback } from 'react';

interface ProgressUpdate {
  type: 'progress';
  phase: string;
  message: string;
  progress: number;
  timestamp: number;
}

interface QueryResult {
  type: 'result';
  success: boolean;
  data: {
    sql: string;
    results: any[];
    visualization: any;
  };
}

interface WebSocketMessage {
  type: 'progress' | 'result' | 'error' | 'cancelled';
  [key: string]: any;
}

export function useQueryWebSocket(sessionId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/query/${sessionId}`);
    
    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'progress':
          setProgress(message as ProgressUpdate);
          break;
        
        case 'result':
          setResult(message as QueryResult);
          setIsProcessing(false);
          setProgress(null);
          break;
        
        case 'error':
          setError(message.message);
          setIsProcessing(false);
          setProgress(null);
          break;
        
        case 'cancelled':
          setIsProcessing(false);
          setProgress(null);
          break;
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error');
    };
    
    wsRef.current = ws;
    
    return () => {
      ws.close();
    };
  }, [sessionId]);

  // Send query
  const sendQuery = useCallback((query: string, keywords: string[] = []) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setIsProcessing(true);
      setResult(null);
      setError(null);
      setProgress(null);
      
      wsRef.current.send(JSON.stringify({
        type: 'query',
        query,
        keywords
      }));
    }
  }, []);

  // Cancel query
  const cancelQuery = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'cancel'
      }));
    }
  }, []);

  return {
    isConnected,
    isProcessing,
    progress,
    result,
    error,
    sendQuery,
    cancelQuery
  };
}


// Usage in component
const QueryInterface: React.FC = () => {
  const { 
    isConnected, 
    isProcessing, 
    progress, 
    result, 
    error,
    sendQuery, 
    cancelQuery 
  } = useQueryWebSocket('session-123');

  return (
    <div>
      {/* Progress indicator */}
      {isProcessing && progress && (
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          <p className="progress-message">{progress.message}</p>
          <p className="progress-percent">{progress.progress.toFixed(0)}%</p>
          <button onClick={cancelQuery}>Cancel</button>
        </div>
      )}
      
      {/* Results */}
      {result && (
        <div className="results">
          <pre>{result.data.sql}</pre>
          {/* Render chart */}
        </div>
      )}
      
      {/* Error */}
      {error && <div className="error">{error}</div>}
    </div>
  );
};
```

---

## 6. Model Format: GGUF

### 6.1 What Is GGUF?

**GGUF** (GGML Universal File) is a binary file format designed specifically for running LLMs efficiently on consumer hardware. It was created by Georgi Gerganov, the developer of **llama.cpp**.

Think of it as the **"portable executable"** for AI models—a single file containing everything needed to run inference:
- Model weights (compressed/quantized)
- Tokenizer vocabulary
- Model architecture metadata
- Configuration parameters

### 6.2 Why GGUF Matters for IDI

```
┌─────────────────────────────────────────────────────────────┐
│                    MODEL FORMAT COMPARISON                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SafeTensors (HuggingFace):                                  │
│  ├── model.safetensors     (weights only)                    │
│  ├── tokenizer.json        (separate file)                   │
│  ├── config.json           (separate file)                   │
│  ├── tokenizer_config.json (separate file)                   │
│  └── Requires: PyTorch, Transformers library                 │
│      Memory: Full precision (FP16/FP32)                      │
│      Speed: Slower inference                                 │
│                                                              │
│  GGUF (llama.cpp):                                           │
│  └── model.gguf            (EVERYTHING in one file)          │
│      ├── Weights (quantized)                                 │
│      ├── Tokenizer                                           │
│      ├── Architecture                                        │
│      └── Config                                              │
│      Requires: llama.cpp only (no Python dependencies)       │
│      Memory: 4-bit quantization (75% smaller)                │
│      Speed: Optimized C++ inference                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Quantization Levels

GGUF supports various quantization levels, trading size for quality:

| Quantization | Size (3B model) | Quality Loss | Speed | IDI Use Case |
|--------------|-----------------|--------------|-------|--------------|
| **Q4_K_M** | ~2.0 GB | ~1-2% | Fast | ✅ **Recommended** |
| Q5_K_M | ~2.5 GB | ~0.5-1% | Medium | Good balance |
| Q8_0 | ~3.5 GB | ~0.1% | Slower | Quality priority |
| F16 | ~6.0 GB | None | Slowest | Won't fit GTX 1650 |

**For your GTX 1650 (4GB VRAM):** Q4_K_M is optimal—fits comfortably with ~2GB overhead for KV cache and LoRA adapters.

### 6.4 Why llama.cpp + GGUF for IDI

1. **Memory Efficiency**: 4-bit quantization means your 3B model uses ~2GB instead of ~6GB
2. **No Python Dependencies**: Pure C++ inference, faster startup
3. **LoRA Hot-Swap**: Load multiple LoRA adapters, switch in <100ms
4. **Cross-Platform**: Same file works on Windows, Linux, macOS
5. **OpenAI-Compatible API**: Built-in server with `/v1/chat/completions` endpoint

### 6.5 The GGUF Workflow for IDI

```
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Start with base model (HuggingFace SafeTensors)          │
│     └── Qwen/Qwen2.5-Coder-3B-Instruct                       │
│                                                              │
│  2. Fine-tune with LoRA on Google Colab                      │
│     └── Creates adapter_model.safetensors (~60MB)            │
│                                                              │
│  3. Export LoRA to GGUF format                               │
│     └── python convert_lora_to_gguf.py                       │
│     └── Creates sql_generator.gguf (~30MB)                   │
│                                                              │
│  4. Download pre-quantized base model (GGUF)                 │
│     └── qwen2.5-coder-3b-instruct-q4_k_m.gguf (~2GB)         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    INFERENCE WORKFLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Start llama.cpp server with base model + LoRA adapters   │
│                                                              │
│     llama-server.exe                                         │
│       -m qwen2.5-coder-3b-instruct-q4_k_m.gguf              │
│       --lora sql_generator.gguf                              │
│       --lora query_understanding.gguf                        │
│       --lora verification.gguf                               │
│       --lora-init-without-apply  # Load but don't apply yet  │
│       --host 127.0.0.1 --port 8080                           │
│       -c 4096  # Context length                              │
│       -ngl 99  # Offload all layers to GPU                   │
│                                                              │
│  2. Switch adapters via API (< 100ms)                        │
│                                                              │
│     POST /lora-adapters                                      │
│     [{"id": 0, "scale": 1.0}]  # Apply sql_generator         │
│                                                              │
│  3. Make inference request                                   │
│                                                              │
│     POST /v1/chat/completions                                │
│     {"messages": [...], "max_tokens": 512}                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.6 Practical Commands

```powershell
# Download pre-quantized base model (recommended)
huggingface-cli download Qwen/Qwen2.5-Coder-3B-Instruct-GGUF `
    qwen2.5-coder-3b-instruct-q4_k_m.gguf `
    --local-dir ./models

# Convert your trained LoRA adapter to GGUF
# (After training in Colab, download the adapter)
python convert_lora_to_gguf.py `
    --input ./adapters/sql_generator `
    --output ./adapters/sql_generator.gguf

# Start llama.cpp server with everything loaded
llama-server.exe `
    -m ./models/qwen2.5-coder-3b-instruct-q4_k_m.gguf `
    --lora ./adapters/sql_generator.gguf `
    --lora ./adapters/query_understanding.gguf `
    --lora ./adapters/verification.gguf `
    --lora-init-without-apply `
    --host 127.0.0.1 `
    --port 8080 `
    -c 4096 `
    -ngl 99

# Test the server
curl http://localhost:8080/health
```

---

## 7. Technology Decision Matrix

### 7.1 Summary of Choices for IDI

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Vector Database** | ChromaDB | Embedded, simple, sufficient scale |
| **Session Storage** | SQLite (dev) → PostgreSQL (prod) | Zero config for dev, Spider compatibility |
| **Visualization** | Recharts | Native React, professional look, simple API |
| **Training Data** | gretelai (primary) + Spider (validation) | Largest synthetic + standard benchmark |
| **Real-Time Updates** | WebSocket via FastAPI | Bidirectional, progress + cancellation |
| **Model Format** | GGUF (Q4_K_M) | 75% smaller, llama.cpp optimized |

### 7.2 Architecture Integration

```
┌─────────────────────────────────────────────────────────────┐
│                      REACT FRONTEND                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Query       │  │ Progress    │  │ Recharts    │          │
│  │ Builder     │  │ Indicator   │  │ Visualizer  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                    WebSocket                                 │
│                          │                                   │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                    FASTAPI BACKEND                           │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐          │
│  │              Multi-Agent Orchestrator          │          │
│  │         (Progress tracking, cancellation)      │          │
│  └───┬───────────┬───────────┬───────────┬───────┘          │
│      │           │           │           │                   │
│  ┌───┴───┐   ┌───┴───┐   ┌───┴───┐   ┌───┴───┐              │
│  │Context│   │Query  │   │SQL    │   │Verify │              │
│  │Manager│   │Under. │   │Gen.   │   │Agent  │              │
│  └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘              │
│      │           │           │           │                   │
│      │           └───────────┴───────────┘                   │
│      │                       │                               │
│      │                       ▼                               │
│      │           ┌─────────────────────┐                     │
│      │           │   llama.cpp Server   │                     │
│      │           │  (GGUF + LoRA)       │                     │
│      │           │  localhost:8080      │                     │
│      │           └─────────────────────┘                     │
│      │                                                       │
│      ▼                                                       │
│  ┌───────────────┐                   ┌───────────────┐       │
│  │   ChromaDB    │                   │    SQLite     │       │
│  │  (Context)    │                   │  (Sessions)   │       │
│  └───────────────┘                   └───────────────┘       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 Implementation Priority

| Week | Focus | Technologies to Implement |
|------|-------|--------------------------|
| **9** | Infrastructure | llama.cpp server, FastAPI scaffold, SQLite sessions |
| **10** | Context System | ChromaDB setup, embedding pipeline, context retrieval |
| **11** | Real-Time | WebSocket endpoints, progress tracking, React hooks |
| **12** | Visualization | Recharts integration, automatic chart selection |

---

## References

### Vector Databases
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Real Python: ChromaDB Tutorial](https://realpython.com/chromadb-vector-database/)
- [RAG with ChromaDB and Ollama](https://dev.to/arjunrao87/simple-wonders-of-rag-using-ollama-langchain-and-chromadb-2hhj)

### Model Formats
- [GGUF Format Specification](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- [HuggingFace GGUF Documentation](https://huggingface.co/docs/hub/en/gguf)
- [Safetensors vs GGUF Comparison](https://learningdeeplearning.com/post/safetensors-vs-gguf/)

### WebSockets
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Streaming with LLMs](https://medium.com/@shubham.mdsk/websocket-based-streaming-with-fast-api-and-local-llama-3-46f88eda71a2)

### Visualization
- [Recharts Documentation](https://recharts.org/en-US/)
- [React Charting Library Comparison](https://stackshare.io/stackups/js-chart-vs-recharts)

### Training Datasets
- [gretelai/synthetic_text_to_sql](https://huggingface.co/datasets/gretelai/synthetic_text_to_sql)
- [Spider Benchmark](https://yale-lily.github.io/spider)
- [Awesome Text2SQL Repository](https://github.com/eosphoros-ai/Awesome-Text2SQL)

---

*Document generated for IDI Project - Universidad Nacional de Colombia*
*Last updated: January 2025*
