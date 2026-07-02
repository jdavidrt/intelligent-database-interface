# Day 1 — Foundations & Contracts
## IDI Implementation Plan

**Goal:** A running skeleton that routes a request through a (stubbed) 7-agent pipeline and can talk to soundwave.

**Gate D1:** `POST /query` with *"How many tracks are standalone singles?"* returns a piped response (understanding → generated SQL → executed against soundwave), with the correct answer using `album_id IS NULL` (EC-03). Progress events visible on `/ws`.

**Pre-condition:** Day 0 complete — `python start.py` brings up llama.cpp + FastAPI + Vite from canonical paths.

---

## Step 1 — Expand `backend/requirements.txt`

Replace the current 4-line file with the full Day 1 dependency set:

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
requests>=2.31.0
psutil>=5.9.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
mysql-connector-python>=9.0.0
sqlglot>=25.0.0
```

Install into the project venv:

```
.venv\Scripts\pip install -r backend/requirements.txt
```

---

## Step 2 — Implement `backend/app/config.py`

Replace the placeholder with a real pydantic-settings `Settings` class. The file must cover every runtime knob used in `main.py` and the new services:

```python
"""Centralised settings for the IDI backend."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # llama.cpp
    llama_cpp_server_url: str = Field(
        default="http://localhost:7860/v1/chat/completions",
        alias="LLAMA_CPP_SERVER_URL",
    )
    llama_cpp_port: int = Field(default=7860, alias="LLAMA_CPP_SERVER_PORT")

    # MySQL / soundwave
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_name: str = Field(default="soundwave_db", alias="DB_NAME")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")

    # Paths
    repo_root: str = Field(default_factory=lambda: os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    ))

    # Backend
    backend_port: int = Field(default=5000, alias="BACKEND_PORT")
    cors_origins: list[str] = Field(default=["*"])

settings = Settings()
```

Create a `.env` file at the **repo root** (add to `.gitignore`):

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=soundwave_db
DB_USER=root
DB_PASSWORD=your_mysql_root_password
LLAMA_CPP_SERVER_PORT=7860
BACKEND_PORT=5000
```

---

## Step 3 — Define Pydantic Envelopes

Create `backend/app/models/__init__.py` (empty) and `backend/app/models/envelope.py`:

```python
"""Shared typed envelopes passed between all agents."""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


# ── DB Profile ────────────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references: Optional[str] = None  # "table.column"
    cardinality: Optional[int] = None  # row count for low-card detection
    sample_values: list[Any] = Field(default_factory=list)
    glossary_note: Optional[str] = None  # human-supplied in survey

class TableInfo(BaseModel):
    name: str
    row_count: Optional[int] = None
    columns: list[ColumnInfo] = Field(default_factory=list)
    description: Optional[str] = None

class DBProfile(BaseModel):
    db_name: str
    domain_description: Optional[str] = None
    tables: list[TableInfo] = Field(default_factory=list)
    relationship_edges: list[tuple[str, str]] = Field(default_factory=list)  # (src_col, tgt_col)
    coded_value_maps: dict[str, dict[str, str]] = Field(default_factory=dict)  # col → {code: meaning}
    glossary: dict[str, str] = Field(default_factory=dict)  # abbrev → meaning
    source_of_truth: dict[str, str] = Field(default_factory=dict)  # ambiguous_col → canonical_col
    sensitivity: dict[str, bool] = Field(default_factory=dict)  # col → hidden
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Intent ────────────────────────────────────────────────────────────────────

class Intent(BaseModel):
    raw_query: str
    entities: list[str] = Field(default_factory=list)       # table/column names mentioned
    metrics: list[str] = Field(default_factory=list)        # COUNT, SUM, AVG …
    filters: list[str] = Field(default_factory=list)        # WHERE conditions in plain words
    time_range: Optional[str] = None
    ambiguity_flags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    plain_restatement: Optional[str] = None   # "What I think you asked"


# ── SQL Candidate ─────────────────────────────────────────────────────────────

class SqlCandidate(BaseModel):
    sql: str
    rationale: Optional[str] = None   # join path explanation
    tables_used: list[str] = Field(default_factory=list)
    columns_used: list[str] = Field(default_factory=list)
    generation_method: Literal["lora", "base_model", "fallback"] = "base_model"


# ── Verification Report ───────────────────────────────────────────────────────

class LayerResult(BaseModel):
    passed: bool
    message: str

class VerifyReport(BaseModel):
    syntax: LayerResult
    semantic: LayerResult
    sanity: LayerResult
    overall_passed: bool
    repaired_sql: Optional[str] = None
    repair_explanation: Optional[str] = None

    @property
    def verdict(self) -> Literal["pass", "fail"]:
        return "pass" if self.overall_passed else "fail"


# ── Agent Event (WebSocket progress) ─────────────────────────────────────────

AgentName = Literal[
    "context_manager",
    "query_understanding",
    "clarification",
    "sql_generator",
    "verification",
    "visualization",
    "session_manager",
    "orchestrator",
]

class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent: AgentName
    status: Literal["started", "progress", "done", "error"]
    message: str
    payload: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Query Result ──────────────────────────────────────────────────────────────

class QueryResult(BaseModel):
    session_id: str
    intent: Optional[Intent] = None
    sql: Optional[SqlCandidate] = None
    verify: Optional[VerifyReport] = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    teaching_summary: Optional[str] = None   # plain-language "why"
    error: Optional[str] = None
```

---

## Step 4 — MySQL Setup & Soundwave Load

### 4a — Install MySQL (if not already running)

Download and install **MySQL Community Server 8.x** for Windows from https://dev.mysql.com/downloads/mysql/. During setup, set `root` password and note it for `.env`.

Verify the server is running:
```
mysql -u root -p -e "SELECT VERSION();"
```

### 4b — Create database and load soundwave

From the repo root in a Windows terminal (or MySQL Workbench):

```sql
CREATE DATABASE IF NOT EXISTS soundwave_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE soundwave_db;
SOURCE soundwave/01_soundwave_schema.sql;
SOURCE soundwave/02_soundwave_data.sql;
```

### 4c — Verify load

```sql
USE soundwave_db;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'soundwave_db';
-- Expected: 19 tables

SELECT 'tracks' AS tbl, COUNT(*) FROM tracks
UNION ALL SELECT 'artists', COUNT(*) FROM artists
UNION ALL SELECT 'albums', COUNT(*) FROM albums
UNION ALL SELECT 'users', COUNT(*) FROM users;
```

---

## Step 5 — Implement `DBConnector` protocol + `MySQLConnector`

Create `backend/app/services/db/connector.py`:

```python
"""DBConnector protocol — thin interface over any relational DB."""

from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from backend.app.models.envelope import DBProfile, TableInfo, ColumnInfo


@runtime_checkable
class DBConnector(Protocol):
    """Read-only DB access + introspection. Concrete implementations: MySQLConnector."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def introspect(self) -> DBProfile: ...
    def execute_read(self, sql: str, limit: int = 200) -> list[dict[str, Any]]: ...
    def explain(self, sql: str) -> bool: ...  # True if MySQL EXPLAIN succeeds
```

Create `backend/app/services/db/mysql_connector.py`:

```python
"""MySQLConnector — soundwave implementation of DBConnector."""

from __future__ import annotations
import mysql.connector
from mysql.connector import MySQLConnection
from typing import Any
import re

from backend.app.config import settings
from backend.app.models.envelope import (
    DBProfile, TableInfo, ColumnInfo,
)


class MySQLConnector:
    def __init__(
        self,
        host: str = settings.db_host,
        port: int = settings.db_port,
        database: str = settings.db_name,
        user: str = settings.db_user,
        password: str = settings.db_password,
    ) -> None:
        self._cfg = dict(host=host, port=port, database=database,
                         user=user, password=password, use_pure=True)
        self._conn: MySQLConnection | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._conn = mysql.connector.connect(**self._cfg)

    def disconnect(self) -> None:
        if self._conn and self._conn.is_connected():
            self._conn.close()
        self._conn = None

    def _cursor(self):
        if not self._conn or not self._conn.is_connected():
            self.connect()
        return self._conn.cursor(dictionary=True)

    # ── introspection ─────────────────────────────────────────────────────────

    def introspect(self) -> DBProfile:
        """Read information_schema and build a DBProfile for soundwave_db."""
        cur = self._cursor()
        db = self._cfg["database"]

        # Tables
        cur.execute(
            "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME", (db,)
        )
        raw_tables = cur.fetchall()

        # Primary keys
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND CONSTRAINT_NAME = 'PRIMARY'", (db,)
        )
        pks: dict[str, set[str]] = {}
        for row in cur.fetchall():
            pks.setdefault(row["TABLE_NAME"], set()).add(row["COLUMN_NAME"])

        # Foreign keys
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            "FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL", (db,)
        )
        fk_rows = cur.fetchall()
        fks: dict[str, dict[str, str]] = {}
        edges: list[tuple[str, str]] = []
        for row in fk_rows:
            ref = f"{row['REFERENCED_TABLE_NAME']}.{row['REFERENCED_COLUMN_NAME']}"
            fks.setdefault(row["TABLE_NAME"], {})[row["COLUMN_NAME"]] = ref
            src = f"{row['TABLE_NAME']}.{row['COLUMN_NAME']}"
            edges.append((src, ref))

        # Columns
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,)
        )
        col_rows = cur.fetchall()
        cols_by_table: dict[str, list[ColumnInfo]] = {}
        for row in col_rows:
            tbl = row["TABLE_NAME"]
            col = ColumnInfo(
                name=row["COLUMN_NAME"],
                data_type=row["DATA_TYPE"],
                is_nullable=row["IS_NULLABLE"] == "YES",
                is_primary_key=row["COLUMN_NAME"] in pks.get(tbl, set()),
                is_foreign_key=row["COLUMN_NAME"] in fks.get(tbl, {}),
                references=fks.get(tbl, {}).get(row["COLUMN_NAME"]),
            )
            cols_by_table.setdefault(tbl, []).append(col)

        tables = [
            TableInfo(
                name=r["TABLE_NAME"],
                row_count=r["TABLE_ROWS"],
                columns=cols_by_table.get(r["TABLE_NAME"], []),
            )
            for r in raw_tables
        ]

        cur.close()
        return DBProfile(db_name=db, tables=tables, relationship_edges=edges)

    # ── read-only execution ───────────────────────────────────────────────────

    def execute_read(self, sql: str, limit: int = 200) -> list[dict[str, Any]]:
        """Execute a SELECT. Raises ValueError on non-SELECT. Injects LIMIT."""
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT"):
            raise ValueError("Only SELECT statements are permitted.")
        sql = self._inject_limit(sql, limit)
        cur = self._cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return rows

    def explain(self, sql: str) -> bool:
        """Return True if MySQL can EXPLAIN the SQL without error."""
        try:
            cur = self._cursor()
            cur.execute(f"EXPLAIN {sql}")
            cur.fetchall()
            cur.close()
            return True
        except Exception:
            return False

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _inject_limit(sql: str, limit: int) -> str:
        """Add LIMIT if not already present."""
        if re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
            return sql
        return sql.rstrip().rstrip(";") + f" LIMIT {limit};"
```

---

## Step 6 — Implement `LLMService`

Create `backend/app/services/llm_service.py`:

```python
"""LLM Service — wraps llama.cpp and exposes LoRA hot-swap + base fallback."""

from __future__ import annotations
import requests
import time
from typing import Any

from backend.app.config import settings


class LLMService:
    """Single point of contact for the llama.cpp inference server."""

    def __init__(self) -> None:
        self._base_url: str = settings.llama_cpp_server_url
        self._active_adapter: str | None = None

    # ── health ────────────────────────────────────────────────────────────────

    def is_healthy(self) -> bool:
        try:
            url = self._base_url.replace("/v1/chat/completions", "/health")
            r = requests.get(url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    # ── inference ─────────────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        timeout: int = 90,
    ) -> str:
        """Send a chat payload to llama.cpp and return the content string."""
        payload: dict[str, Any] = {"messages": messages, "temperature": temperature}
        t0 = time.time()
        try:
            resp = requests.post(self._base_url, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"llama.cpp timed out after {timeout}s.")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach llama.cpp at {self._base_url}. Is it running?"
            )
        data = resp.json()
        content: str = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        elapsed = round((time.time() - t0) * 1000)
        print(f"[LLMService] {elapsed}ms — {len(content)} chars returned")
        return content

    # ── LoRA adapter hot-swap (stub, wired Day 4) ─────────────────────────────

    def load_adapter(self, adapter_name: str) -> None:
        """Hot-swap a LoRA adapter. Placeholder until Day 4 wires llama.cpp /lora-adapters."""
        print(f"[LLMService] adapter stub: {adapter_name} (hot-swap wired Day 4)")
        self._active_adapter = adapter_name

    def active_adapter(self) -> str | None:
        return self._active_adapter


# Module-level singleton — import this everywhere.
llm_service = LLMService()
```

---

## Step 7 — Orchestrator Skeleton

Create `backend/app/services/orchestrator.py`:

```python
"""Orchestrator — deterministic 7-agent pipeline with per-step AgentEvent emission."""

from __future__ import annotations
import uuid
from typing import AsyncGenerator, Any
import asyncio

from backend.app.models.envelope import (
    AgentEvent, AgentName, DBProfile, Intent, SqlCandidate,
    VerifyReport, LayerResult, QueryResult,
)
from backend.app.services.llm_service import llm_service
from backend.app.services.db.mysql_connector import MySQLConnector


class Orchestrator:
    def __init__(self) -> None:
        self._db: MySQLConnector = MySQLConnector()
        self._db_profile: DBProfile | None = None

    # ── event helpers ─────────────────────────────────────────────────────────

    def _event(
        self,
        session_id: str,
        agent: AgentName,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentEvent:
        return AgentEvent(
            session_id=session_id,
            agent=agent,
            status=status,
            message=message,
            payload=payload,
        )

    # ── pipeline ──────────────────────────────────────────────────────────────

    async def run(
        self, query: str, session_id: str | None = None
    ) -> AsyncGenerator[AgentEvent | QueryResult, None]:
        """
        Yield AgentEvents as each stage completes, then yield the final QueryResult.
        The pipeline is:
          1. context_manager (load DBProfile)
          2. query_understanding (Intent)
          3. clarification (if ambiguity_flags non-empty — skipped Day 1)
          4. sql_generator (SqlCandidate via fallback loop)
          5. verification (3-layer check)
          6. execution (read-only via MySQLConnector)
          7. visualization (chart spec — stubbed Day 1)
        """
        sid = session_id or str(uuid.uuid4())
        result = QueryResult(session_id=sid)

        # ── 1. Context Manager ────────────────────────────────────────────────
        yield self._event(sid, "context_manager", "started", "Loading DB profile…")
        try:
            self._db.connect()
            if self._db_profile is None:
                self._db_profile = self._db.introspect()
            yield self._event(sid, "context_manager", "done",
                              f"DB profile loaded: {len(self._db_profile.tables)} tables",
                              {"table_count": len(self._db_profile.tables)})
        except Exception as e:
            yield self._event(sid, "context_manager", "error", str(e))
            result.error = str(e)
            yield result
            return

        # ── 2. Query Understanding (stub — Day 2 replaces) ────────────────────
        yield self._event(sid, "query_understanding", "started", "Parsing intent…")
        intent = Intent(
            raw_query=query,
            plain_restatement=f"You asked: '{query}'",
        )
        result.intent = intent
        yield self._event(sid, "query_understanding", "done",
                          f"Intent parsed: '{intent.plain_restatement}'",
                          intent.model_dump())

        # ── 3. SQL Generator (fallback: sandbox chat loop) ────────────────────
        yield self._event(sid, "sql_generator", "started", "Generating SQL…")
        try:
            sql_text = self._generate_sql_fallback(query)
            candidate = SqlCandidate(sql=sql_text, generation_method="fallback")
            result.sql = candidate
            yield self._event(sid, "sql_generator", "done",
                              "SQL generated via fallback loop",
                              {"sql": sql_text[:200]})
        except Exception as e:
            yield self._event(sid, "sql_generator", "error", str(e))
            result.error = str(e)
            yield result
            return

        # ── 4. Verification (stub — Day 2 adds full 3-layer chain) ────────────
        yield self._event(sid, "verification", "started", "Verifying SQL…")
        verify = self._verify_stub(candidate.sql)
        result.verify = verify
        if not verify.overall_passed:
            yield self._event(sid, "verification", "error",
                              "SQL failed verification — not executed",
                              verify.model_dump())
            result.error = "Verification failed."
            yield result
            return
        yield self._event(sid, "verification", "done", "SQL passed verification",
                          verify.model_dump())

        # ── 5. Execution ──────────────────────────────────────────────────────
        yield self._event(sid, "orchestrator", "progress", "Executing SQL against soundwave…")
        try:
            rows = self._db.execute_read(candidate.sql)
            result.rows = rows
            result.row_count = len(rows)
            yield self._event(sid, "orchestrator", "done",
                              f"Executed. {len(rows)} row(s) returned.",
                              {"row_count": len(rows)})
        except Exception as e:
            yield self._event(sid, "orchestrator", "error", str(e))
            result.error = str(e)

        yield result

    # ── SQL generation fallback (sandbox chat loop) ───────────────────────────

    def _generate_sql_fallback(self, query: str) -> str:
        """
        Reproduce the sandbox /chat approach: build a system prompt from context
        and ask llama.cpp to generate SQL. Extract the ```sql block.
        """
        import os, re
        app_dir = os.path.dirname(os.path.abspath(__file__ + "/.."))
        context_dir = os.path.join(app_dir, "context")
        context = ""
        if os.path.isdir(context_dir):
            for fn in sorted(os.listdir(context_dir)):
                fp = os.path.join(context_dir, fn)
                if os.path.isfile(fp):
                    try:
                        with open(fp, encoding="utf-8") as f:
                            context += f"\n\n--- {fn} ---\n" + f.read()
                    except Exception:
                        pass

        system = (
            "You are IDI, an NL2SQL assistant for the soundwave_db MySQL database. "
            "Generate a single correct SELECT statement. "
            "Respond with ONLY a ```sql ... ``` block.\n\n"
            "DATABASE CONTEXT:\n" + context
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ]
        raw = llm_service.chat(messages)
        match = re.search(r"```sql\s*([\s\S]*?)```", raw, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # If no block found, return the whole response as best-effort
        return raw.strip()

    # ── verification stub ─────────────────────────────────────────────────────

    def _verify_stub(self, sql: str) -> VerifyReport:
        """
        Day 1: minimal verification — only check it is a SELECT.
        Day 2 replaces with the full 3-layer chain.
        """
        is_select = sql.strip().upper().startswith("SELECT")
        layer = LayerResult(
            passed=is_select,
            message="SELECT guard passed" if is_select else "Non-SELECT statement rejected",
        )
        return VerifyReport(
            syntax=layer,
            semantic=LayerResult(passed=is_select, message="Stub — Day 2"),
            sanity=LayerResult(passed=is_select, message="Stub — Day 2"),
            overall_passed=is_select,
        )


# Module-level singleton.
orchestrator = Orchestrator()
```

---

## Step 8 — API Routes

### 8a — `backend/app/api/routes/health.py`

```python
"""GET /health — liveness probe."""

from fastapi import APIRouter
from backend.app.services.llm_service import llm_service

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm_healthy": llm_service.is_healthy(),
    }
```

### 8b — `backend/app/api/routes/query.py`

```python
"""POST /query — main entry point."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from backend.app.services.orchestrator import orchestrator
from backend.app.models.envelope import AgentEvent, QueryResult

router = APIRouter()


class QueryRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/query")
async def query(req: QueryRequest):
    """
    Run the 7-agent pipeline and stream NDJSON.
    Each line is either an AgentEvent or the final QueryResult (type='result').
    """
    async def _stream():
        async for event in orchestrator.run(req.message, req.session_id):
            if isinstance(event, AgentEvent):
                line = event.model_dump_json() + "\n"
            elif isinstance(event, QueryResult):
                data = event.model_dump()
                data["type"] = "result"
                line = json.dumps(data, default=str) + "\n"
            else:
                line = json.dumps({"raw": str(event)}) + "\n"
            yield line

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
```

### 8c — `backend/app/api/routes/db.py`

```python
"""GET /db/profile — return the current DBProfile."""

from fastapi import APIRouter, HTTPException
from backend.app.services.orchestrator import orchestrator

router = APIRouter()

@router.get("/db/profile")
def db_profile():
    if orchestrator._db_profile is None:
        raise HTTPException(status_code=404, detail="DBProfile not loaded yet. Run a query first.")
    return orchestrator._db_profile.model_dump(mode="json")
```

### 8d — `backend/app/api/routes/session.py`

```python
"""Session routes — stub for Day 2."""

from fastapi import APIRouter

router = APIRouter()

@router.get("/session/{session_id}")
def get_session(session_id: str):
    return {"session_id": session_id, "note": "Session persistence wired Day 2."}
```

---

## Step 9 — WebSocket `/ws`

Replace the placeholder in `backend/app/api/websocket.py`:

```python
"""WebSocket /ws — streams AgentEvents for the ProgressIndicator."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.orchestrator import orchestrator
from backend.app.models.envelope import AgentEvent, QueryResult
import json

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("message", "")
            session_id = data.get("session_id")

            async for event in orchestrator.run(query, session_id):
                if isinstance(event, AgentEvent):
                    await websocket.send_text(event.model_dump_json())
                elif isinstance(event, QueryResult):
                    payload = event.model_dump()
                    payload["type"] = "result"
                    await websocket.send_text(json.dumps(payload, default=str))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
```

---

## Step 10 — Wire Everything into `main.py`

Edit `backend/app/main.py` to mount the new routes **above** the existing `/chat` and `/benchmark` endpoints. Add these imports and registrations near the top:

```python
# Add these imports after existing imports:
from backend.app.api.routes import health, query as query_route, db as db_route, session as session_route
from backend.app.api import websocket as ws_module

# Add after app = FastAPI(...) and CORS middleware:
app.include_router(health.router)
app.include_router(query_route.router)
app.include_router(db_route.router)
app.include_router(session_route.router)
app.include_router(ws_module.router)
```

The legacy `/chat` and `/benchmark` endpoints remain — they are the fallback proof.

---

## Step 11 — Install New Dependencies & Smoke-Test

```
.venv\Scripts\pip install mysql-connector-python pydantic-settings sqlglot python-dotenv
```

Then restart the backend:

```
python start.py
```

Verify each new route:

```
curl http://localhost:5000/health
# Expected: {"status":"ok","llm_healthy":true/false}

curl http://localhost:5000/db/profile
# Expected: 404 until first query runs (correct)

curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How many tracks are standalone singles?\"}"
# Expected: NDJSON stream with AgentEvents followed by a result object
```

---

## Step 12 — Kick Off Colab Training (Manual)

> This is a human step — Cowork cannot run Colab notebooks.

Open `training/training_pipeline.py` in Colab (or upload it). Launch `sql_generator` training with:

- Dataset: `gretelai/synthetic_text_to_sql` + soundwave-style samples from `data/synthetic/`
- Config: `r=16, alpha=32, dropout=0.05`, attention+MLP modules, 3 epochs, lr `2e-4`, QLoRA 4-bit
- Export: GGUF Q4_K_M → `adapters/sql_generator.gguf`

The ≤ 8 h clock starts now. Base-model fallback means nothing blocks while this trains.

---

## Gate D1 Verification

Run this end-to-end check:

```
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How many tracks are standalone singles?\"}"
```

**Pass criteria:**
1. Stream contains `AgentEvent` entries for `context_manager`, `query_understanding`, `sql_generator`, `verification`, `orchestrator`.
2. Final `result` object has `rows` with a count.
3. Generated SQL contains `album_id IS NULL` (EC-03 handling).
4. `GET /health` returns 200.
5. WebSocket `/ws` accepts a connection and echoes events for the same query (test via browser console or `wscat`).

---

## File Checklist

Files created or significantly modified during Day 1:

| File | Action |
|---|---|
| `backend/requirements.txt` | Updated |
| `.env` (repo root) | Created (gitignored) |
| `backend/app/config.py` | Implemented |
| `backend/app/models/__init__.py` | Created |
| `backend/app/models/envelope.py` | Created |
| `backend/app/services/db/connector.py` | Created |
| `backend/app/services/db/mysql_connector.py` | Created |
| `backend/app/services/llm_service.py` | Created |
| `backend/app/services/orchestrator.py` | Created |
| `backend/app/api/routes/health.py` | Created |
| `backend/app/api/routes/query.py` | Created |
| `backend/app/api/routes/db.py` | Created |
| `backend/app/api/routes/session.py` | Created |
| `backend/app/api/websocket.py` | Implemented |
| `backend/app/main.py` | Routers mounted |
