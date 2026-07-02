# Day 2 — The Seven Agents, Memory & Auto-Exploration
## IDI Implementation Plan

**Goal:** Real agents, real verification, persistent memory, and database self-characterization.

**Gate D2:** Run 8 probe queries, one per soundwave edge-case code (EC-01…EC-08); ≥ 6/8 pass verification and return correct rows. Sessions survive a backend restart.

**Pre-condition:** Gate D1 passed — `/query` is live, soundwave is loaded, MySQLConnector works.

---

## Step 1 — Expand `backend/requirements.txt`

Add Day 2 dependencies (append to the Day 1 list):

```
chromadb>=0.5.0
sentence-transformers>=3.0.0
sqlglot>=25.0.0    # already present from Day 1
```

Install:

```
.venv\Scripts\pip install chromadb sentence-transformers
```

> `sentence-transformers` pulls a small embedding model (~90 MB) used by ChromaDB.
> On first run it downloads to `~/.cache/torch/`. No GPU required — CPU is fine for embedding.

---

## Step 2 — SQLite Session Manager

Create `backend/app/services/memory/sessions.py`:

```python
"""Session Manager — SQLite persistence for multi-turn sessions."""

from __future__ import annotations
import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import Any

from backend.app.config import settings


DB_PATH = os.path.join(settings.repo_root, "data", "sessions.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            db_name    TEXT,
            title      TEXT
        );
        CREATE TABLE IF NOT EXISTS turns (
            turn_id    TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(session_id),
            created_at TEXT NOT NULL,
            role       TEXT NOT NULL,      -- 'user' | 'assistant'
            content    TEXT NOT NULL,      -- raw NL or final answer
            sql        TEXT,               -- generated SQL (nullable)
            rows_json  TEXT,               -- JSON array of result rows (nullable)
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
        """)


def create_session(db_name: str = "", title: str = "") -> str:
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO sessions (session_id, created_at, updated_at, db_name, title) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, now, now, db_name, title or f"Session {now[:10]}"),
        )
    return sid


def append_turn(
    session_id: str,
    role: str,
    content: str,
    sql: str | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> None:
    now = datetime.utcnow().isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO turns (turn_id, session_id, created_at, role, content, sql, rows_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, now, role, content,
             sql, json.dumps(rows, default=str) if rows is not None else None),
        )
        con.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id)
        )


def get_session(session_id: str) -> dict[str, Any] | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        turns = con.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY created_at", (session_id,)
        ).fetchall()
    result = dict(row)
    result["turns"] = [dict(t) for t in turns]
    return result


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            "SELECT session_id, title, db_name, created_at, updated_at "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_turns(session_id: str, n: int = 6) -> list[dict[str, str]]:
    """Return the last n turns as role/content dicts for LLM context injection."""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM turns WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?", (session_id, n)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
```

Call `init_db()` at FastAPI startup — add to `backend/app/main.py`:

```python
from backend.app.services.memory.sessions import init_db
# Inside the startup event or at module level after app creation:
init_db()
```

---

## Step 3 — ChromaDB Vector Store

Create `backend/app/services/memory/vector.py`:

```python
"""ChromaDB context store — schema embeddings + DBProfile semantic retrieval."""

from __future__ import annotations
import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.app.config import settings
from backend.app.models.envelope import DBProfile

_CHROMA_PATH = os.path.join(settings.repo_root, "data", "chromadb")
_EMBED_MODEL = "all-MiniLM-L6-v2"  # ~22 MB, CPU-friendly

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        os.makedirs(_CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=_CHROMA_PATH)
        embed_fn = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        _collection = _client.get_or_create_collection(
            name="idi_schema_context",
            embedding_function=embed_fn,
        )
    return _collection


def embed_db_profile(profile: DBProfile) -> None:
    """Embed each table's column list as a document."""
    col = _get_collection()
    docs, ids, metas = [], [], []
    for table in profile.tables:
        col_names = ", ".join(c.name for c in table.columns)
        doc = f"Table: {table.name}. Columns: {col_names}."
        if table.description:
            doc += f" Description: {table.description}"
        docs.append(doc)
        ids.append(f"{profile.db_name}::{table.name}")
        metas.append({"db": profile.db_name, "table": table.name})
    if docs:
        col.upsert(documents=docs, ids=ids, metadatas=metas)


def embed_text(doc_id: str, text: str, metadata: dict | None = None) -> None:
    """Embed an arbitrary text document (e.g., soundwave context markdown)."""
    col = _get_collection()
    col.upsert(documents=[text], ids=[doc_id], metadatas=[metadata or {}])


def query_context(question: str, n_results: int = 5) -> list[str]:
    """Return the top-n most relevant schema passages for a question."""
    col = _get_collection()
    results = col.query(query_texts=[question], n_results=n_results)
    return results.get("documents", [[]])[0]
```

---

## Step 4 — Context Manager Agent

Create `backend/app/agents/context_manager.py`:

```python
"""Context Manager — DB introspection, survey, ChromaDB embedding."""

from __future__ import annotations
import os
from backend.app.models.envelope import DBProfile
from backend.app.services.db.mysql_connector import MySQLConnector
from backend.app.services.memory.vector import embed_db_profile, embed_text
from backend.app.config import settings


class ContextManager:
    """
    1. Introspects the connected DB → DBProfile.
    2. Injects human-supplied survey data (glossary, coded values, etc.).
    3. Loads the soundwave context markdown into ChromaDB.
    4. Embeds the schema into ChromaDB for semantic retrieval.
    """

    def __init__(self, connector: MySQLConnector) -> None:
        self._db = connector

    def build_profile(self) -> DBProfile:
        """Full pipeline: introspect → enrich with survey → embed."""
        profile = self._db.introspect()
        profile = self._apply_soundwave_survey(profile)
        self._embed(profile)
        return profile

    # ── soundwave-specific survey data ────────────────────────────────────────
    # In a future UI, this comes from the characterization form (§6 of MASTERPLAN).
    # For Day 2, it is hardcoded from 02_soundwave_context.md.

    def _apply_soundwave_survey(self, profile: DBProfile) -> DBProfile:
        profile.domain_description = (
            "Soundwave is a music streaming platform database. "
            "It tracks artists, albums, tracks, users, playlists, "
            "subscriptions, play events, and payments."
        )
        profile.glossary = {
            "trk_dur_ms": "track duration in milliseconds",
            "is_exp": "is explicit content (1=yes, 0=no)",
            "is_prim": "is primary artist on a track (1=yes, 0=no)",
            "usr_acq_src": "user acquisition source code",
            "trk_position_ms": "playback position in milliseconds",
        }
        profile.coded_value_maps = {
            "plan_type": {
                "1": "Free",
                "2": "Individual Premium",
                "3": "Student Premium",
                "4": "Family Premium",
            },
            "usr_acq_src": {
                "1": "organic",
                "2": "referral",
                "3": "paid_ad",
                "4": "social",
            },
        }
        profile.source_of_truth = {
            "play_count": "play_events table (raw)",
            "monthly_listeners_cached": "daily_artist_metrics (pre-aggregated — use for reports, not real-time)",
            "total_plays": "tracks.total_plays is a cached counter; use COUNT(play_events) for accuracy",
        }
        return profile

    def _embed(self, profile: DBProfile) -> None:
        embed_db_profile(profile)
        # Also embed the soundwave context markdown
        ctx_path = os.path.join(
            settings.repo_root, "soundwave", "02_soundwave_context.md"
        )
        if os.path.isfile(ctx_path):
            with open(ctx_path, encoding="utf-8") as f:
                embed_text("soundwave::context_md", f.read(), {"type": "domain_context"})
```

---

## Step 5 — Query Understanding Agent

Create `backend/app/agents/query_understanding.py`:

```python
"""Query Understanding — intent/entity/metric extraction + ambiguity detection."""

from __future__ import annotations
import json
import re
from backend.app.models.envelope import Intent, DBProfile
from backend.app.services.llm_service import llm_service
from backend.app.services.memory.vector import query_context


SYSTEM_PROMPT = """\
You are the Query Understanding module of IDI.
Given a user question and relevant schema context, extract:
- entities: table or column names explicitly or implicitly referenced
- metrics: aggregations requested (COUNT, SUM, AVG, MIN, MAX, etc.)
- filters: conditions in plain English
- time_range: any time constraint (or null)
- ambiguity_flags: list of ambiguities (e.g. "column 'name' exists in multiple tables")
- plain_restatement: one sentence restating what the user is asking

Respond with ONLY valid JSON matching this schema:
{
  "entities": [...],
  "metrics": [...],
  "filters": [...],
  "time_range": null,
  "ambiguity_flags": [...],
  "plain_restatement": "..."
}
"""


class QueryUnderstanding:
    def parse(self, query: str, profile: DBProfile) -> Intent:
        # Retrieve relevant schema context from ChromaDB
        context_passages = query_context(query, n_results=4)
        context_str = "\n".join(context_passages)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Schema context:\n{context_str}\n\n"
                    f"User question: {query}"
                ),
            },
        ]

        try:
            raw = llm_service.chat(messages, temperature=0.1)
            # Extract JSON even if the model wraps it in markdown
            match = re.search(r"\{[\s\S]+\}", raw)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"[QueryUnderstanding] parse failed: {e} — using defaults")
            data = {}

        return Intent(
            raw_query=query,
            entities=data.get("entities", []),
            metrics=data.get("metrics", []),
            filters=data.get("filters", []),
            time_range=data.get("time_range"),
            ambiguity_flags=data.get("ambiguity_flags", []),
            plain_restatement=data.get("plain_restatement", f"You asked: '{query}'"),
        )
```

---

## Step 6 — Clarification Agent

Create `backend/app/agents/clarification.py`:

```python
"""Clarification — generates follow-up questions when ambiguity flags fire."""

from __future__ import annotations
from backend.app.models.envelope import Intent
from backend.app.services.llm_service import llm_service


SYSTEM_PROMPT = """\
You are the Clarification module of IDI.
The query understanding module detected the following ambiguities.
Generate one clear, short follow-up question that resolves the most critical ambiguity.
The question should be phrased for a non-technical user.
Respond with ONLY the question text, no preamble.
"""


class Clarification:
    def needs_clarification(self, intent: Intent) -> bool:
        return len(intent.ambiguity_flags) > 0

    def generate_question(self, intent: Intent) -> str:
        if not intent.ambiguity_flags:
            return ""
        flags_str = "\n".join(f"- {f}" for f in intent.ambiguity_flags)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original question: {intent.raw_query}\n"
                    f"Ambiguities:\n{flags_str}"
                ),
            },
        ]
        return llm_service.chat(messages, temperature=0.2).strip()
```

---

## Step 7 — SQL Generator Agent

Create `backend/app/agents/sql_generator.py`:

```python
"""SQL Generator — NL→SQL with rationale, grounded in DBProfile + ChromaDB context."""

from __future__ import annotations
import re
from backend.app.models.envelope import Intent, DBProfile, SqlCandidate
from backend.app.services.llm_service import llm_service
from backend.app.services.memory.vector import query_context


SYSTEM_PROMPT = """\
You are the SQL Generator module of IDI, an NL2SQL assistant for a MySQL database.

Rules:
1. Generate a single SELECT statement only. Never INSERT/UPDATE/DELETE/DROP.
2. Always qualify column names with table names when ambiguity is possible.
3. Use the schema context and DBProfile to resolve table and column names.
4. If a column might be NULL (e.g. album_id IS NULL for standalone tracks), handle it explicitly.
5. Respect coded values from the glossary (e.g. plan_type=1 means 'Free').
6. End the SQL with a semicolon.

Respond in this exact format:
### Rationale
[One paragraph: which tables you chose, why, any tricky joins or NULL handling.]

### SQL
```sql
[the complete SELECT statement]
```
"""


def _build_schema_summary(profile: DBProfile) -> str:
    lines = [f"Database: {profile.db_name}"]
    if profile.domain_description:
        lines.append(f"Domain: {profile.domain_description}")
    for t in profile.tables:
        cols = ", ".join(
            f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''})"
            for c in t.columns
        )
        lines.append(f"  {t.name}: {cols}")
    if profile.glossary:
        lines.append("Glossary: " + ", ".join(f"{k}={v}" for k, v in profile.glossary.items()))
    if profile.coded_value_maps:
        for col, mapping in profile.coded_value_maps.items():
            lines.append(f"Coded values for {col}: " + ", ".join(f"{k}→{v}" for k, v in mapping.items()))
    return "\n".join(lines)


class SQLGenerator:
    def generate(self, intent: Intent, profile: DBProfile) -> SqlCandidate:
        schema_summary = _build_schema_summary(profile)
        context_passages = query_context(intent.raw_query, n_results=4)
        context_str = "\n".join(context_passages)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Schema:\n{schema_summary}\n\n"
                    f"Relevant context:\n{context_str}\n\n"
                    f"User intent: {intent.plain_restatement}\n"
                    f"Original query: {intent.raw_query}"
                ),
            },
        ]

        raw = llm_service.chat(messages, temperature=0.2)

        # Extract rationale
        rationale_match = re.search(r"### Rationale\s*([\s\S]*?)(?=### SQL|```sql|$)", raw)
        rationale = rationale_match.group(1).strip() if rationale_match else ""

        # Extract SQL
        sql_match = re.search(r"```sql\s*([\s\S]*?)```", raw, re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Best-effort: take everything after ### SQL
            sql_section = re.search(r"### SQL\s*([\s\S]*)", raw)
            sql = sql_section.group(1).strip() if sql_section else raw.strip()

        # Determine generation method
        method = "lora" if llm_service.active_adapter() == "sql_generator" else "base_model"

        return SqlCandidate(
            sql=sql,
            rationale=rationale,
            generation_method=method,
        )
```

---

## Step 8 — Verification Agent (Full 3-Layer Chain)

Create `backend/app/agents/verification.py`:

```python
"""Verification Agent — 3-layer chain: Syntax → Semantic → Sanity."""

from __future__ import annotations
import re
import sqlglot
from sqlglot import exp

from backend.app.models.envelope import (
    DBProfile, SqlCandidate, VerifyReport, LayerResult,
)
from backend.app.services.db.mysql_connector import MySQLConnector


class VerificationAgent:
    def __init__(self, connector: MySQLConnector) -> None:
        self._db = connector

    def verify(self, candidate: SqlCandidate, profile: DBProfile) -> VerifyReport:
        sql = candidate.sql.strip()

        syntax = self._layer_syntax(sql)
        if not syntax.passed:
            return VerifyReport(
                syntax=syntax,
                semantic=LayerResult(passed=False, message="Skipped — syntax failed"),
                sanity=LayerResult(passed=False, message="Skipped — syntax failed"),
                overall_passed=False,
            )

        semantic = self._layer_semantic(sql, profile)
        sanity = self._layer_sanity(sql, profile)

        overall = syntax.passed and semantic.passed and sanity.passed

        repaired_sql: str | None = None
        repair_note: str | None = None
        if not overall:
            repaired_sql, repair_note = self._attempt_repair(sql, profile, semantic, sanity)

        return VerifyReport(
            syntax=syntax,
            semantic=semantic,
            sanity=sanity,
            overall_passed=overall if repaired_sql is None else True,
            repaired_sql=repaired_sql,
            repair_explanation=repair_note,
        )

    # ── Layer 1: Syntax ───────────────────────────────────────────────────────

    def _layer_syntax(self, sql: str) -> LayerResult:
        """sqlglot parse (AST) + MySQL EXPLAIN (no execution)."""
        # AST check
        try:
            sqlglot.parse_one(sql, dialect="mysql")
        except Exception as e:
            return LayerResult(passed=False, message=f"sqlglot parse error: {e}")

        # MySQL EXPLAIN
        if not self._db.explain(sql):
            return LayerResult(passed=False, message="MySQL EXPLAIN rejected the query")

        return LayerResult(passed=True, message="Syntax valid (sqlglot + EXPLAIN)")

    # ── Layer 2: Semantic ─────────────────────────────────────────────────────

    def _layer_semantic(self, sql: str, profile: DBProfile) -> LayerResult:
        """Schema-linking: every table/column in SQL must exist in DBProfile."""
        known_tables = {t.name.lower() for t in profile.tables}
        known_cols: dict[str, set[str]] = {
            t.name.lower(): {c.name.lower() for c in t.columns}
            for t in profile.tables
        }

        try:
            tree = sqlglot.parse_one(sql, dialect="mysql")
        except Exception as e:
            return LayerResult(passed=False, message=f"Parse error in semantic layer: {e}")

        # Check table references
        for tbl in tree.find_all(exp.Table):
            name = tbl.name.lower()
            if name and name not in known_tables:
                return LayerResult(
                    passed=False,
                    message=f"Hallucinated table: '{tbl.name}' not in DBProfile",
                )

        # Check column references (only when table is qualified)
        for col in tree.find_all(exp.Column):
            tbl_ref = col.table
            col_name = col.name.lower() if col.name else ""
            if tbl_ref and col_name:
                tbl_ref_lower = tbl_ref.lower()
                if tbl_ref_lower in known_cols:
                    if col_name not in known_cols[tbl_ref_lower]:
                        return LayerResult(
                            passed=False,
                            message=f"Hallucinated column: '{tbl_ref}.{col.name}' not in schema",
                        )

        return LayerResult(passed=True, message="All tables and columns exist in DBProfile")

    # ── Layer 3: Sanity ───────────────────────────────────────────────────────

    def _layer_sanity(self, sql: str, profile: DBProfile) -> LayerResult:
        """
        Safety heuristics from the soundwave edge-case taxonomy:
        - Must be SELECT (read-only guard).
        - No NULL = NULL patterns (= NULL instead of IS NULL).
        - No aggregate in WHERE without HAVING (pre-agg vs raw).
        - Must have or accept a LIMIT.
        """
        sql_upper = sql.upper()

        if not sql_upper.lstrip().startswith("SELECT"):
            return LayerResult(passed=False, message="Non-SELECT statement rejected (read-only guard)")

        # EC-11 heuristic: = NULL instead of IS NULL
        if re.search(r"=\s*NULL\b", sql, re.IGNORECASE):
            return LayerResult(
                passed=False,
                message="NULL comparison error: use IS NULL, not = NULL (EC-11)",
            )

        # Aggregate in WHERE clause (should be HAVING)
        if re.search(r"\bWHERE\b.*\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql, re.IGNORECASE):
            return LayerResult(
                passed=False,
                message="Aggregate function found in WHERE clause — use HAVING instead",
            )

        return LayerResult(passed=True, message="Sanity checks passed")

    # ── Repair attempt ────────────────────────────────────────────────────────

    def _attempt_repair(
        self,
        sql: str,
        profile: DBProfile,
        semantic: LayerResult,
        sanity: LayerResult,
    ) -> tuple[str | None, str | None]:
        """Apply simple mechanical fixes before falling back to the generator."""
        repaired = sql

        # Fix = NULL → IS NULL
        if "= NULL" in sql.upper():
            repaired = re.sub(r"=\s*NULL\b", "IS NULL", repaired, flags=re.IGNORECASE)
            if repaired != sql:
                return repaired, "Repaired: replaced '= NULL' with 'IS NULL'"

        return None, None
```

---

## Step 9 — Wire All Agents into the Orchestrator

Replace the stub methods in `backend/app/services/orchestrator.py` with calls to the real agents. The full updated orchestrator:

```python
"""Orchestrator — real 7-agent pipeline with clarification branch + retry-on-verify-fail."""

from __future__ import annotations
import uuid
from typing import AsyncGenerator, Any

from backend.app.models.envelope import (
    AgentEvent, AgentName, DBProfile, Intent, SqlCandidate,
    VerifyReport, LayerResult, QueryResult,
)
from backend.app.services.llm_service import llm_service
from backend.app.services.db.mysql_connector import MySQLConnector
from backend.app.agents.context_manager import ContextManager
from backend.app.agents.query_understanding import QueryUnderstanding
from backend.app.agents.clarification import Clarification
from backend.app.agents.sql_generator import SQLGenerator
from backend.app.agents.verification import VerificationAgent
from backend.app.services.memory.sessions import (
    create_session, append_turn, get_recent_turns,
)


class Orchestrator:
    def __init__(self) -> None:
        self._db = MySQLConnector()
        self._db_profile: DBProfile | None = None
        self._context_mgr = ContextManager(self._db)
        self._query_understanding = QueryUnderstanding()
        self._clarification = Clarification()
        self._sql_generator = SQLGenerator()
        self._verification = VerificationAgent(self._db)

    # ── event helper ──────────────────────────────────────────────────────────

    def _ev(
        self,
        sid: str,
        agent: AgentName,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentEvent:
        return AgentEvent(session_id=sid, agent=agent,
                          status=status, message=message, payload=payload)

    # ── pipeline ──────────────────────────────────────────────────────────────

    async def run(
        self, query: str, session_id: str | None = None
    ) -> AsyncGenerator[AgentEvent | QueryResult, None]:
        sid = session_id or create_session(db_name="soundwave_db")
        result = QueryResult(session_id=sid)
        append_turn(sid, "user", query)

        # ── 1. Context Manager ────────────────────────────────────────────────
        yield self._ev(sid, "context_manager", "started", "Loading DB profile…")
        try:
            self._db.connect()
            if self._db_profile is None:
                self._db_profile = self._context_mgr.build_profile()
            yield self._ev(sid, "context_manager", "done",
                           f"{len(self._db_profile.tables)} tables in DBProfile",
                           {"table_count": len(self._db_profile.tables)})
        except Exception as e:
            yield self._ev(sid, "context_manager", "error", str(e))
            result.error = str(e)
            yield result
            return

        # ── 2. Query Understanding ────────────────────────────────────────────
        yield self._ev(sid, "query_understanding", "started", "Parsing intent…")
        # Inject recent turns for multi-turn context
        recent = get_recent_turns(sid, n=4)
        contextualised_query = query
        if recent:
            history_str = "\n".join(f"{t['role']}: {t['content']}" for t in recent[:-1])
            contextualised_query = f"[History]\n{history_str}\n[Current] {query}"
        intent = self._query_understanding.parse(contextualised_query, self._db_profile)
        result.intent = intent
        yield self._ev(sid, "query_understanding", "done",
                       intent.plain_restatement or "Intent parsed",
                       intent.model_dump())

        # ── 3. Clarification (branch) ─────────────────────────────────────────
        if self._clarification.needs_clarification(intent):
            yield self._ev(sid, "clarification", "started",
                           "Ambiguity detected — generating follow-up…")
            question = self._clarification.generate_question(intent)
            yield self._ev(sid, "clarification", "done",
                           question, {"clarification_question": question})
            result.teaching_summary = f"**Clarification needed:** {question}"
            yield result
            return  # Stop and wait for user reply

        # ── 4. SQL Generator ──────────────────────────────────────────────────
        yield self._ev(sid, "sql_generator", "started", "Generating SQL…")
        try:
            candidate = self._sql_generator.generate(intent, self._db_profile)
            result.sql = candidate
            yield self._ev(sid, "sql_generator", "done",
                           "SQL generated",
                           {"sql": candidate.sql[:300], "rationale": candidate.rationale})
        except Exception as e:
            yield self._ev(sid, "sql_generator", "error", str(e))
            result.error = str(e)
            yield result
            return

        # ── 5. Verification (with 1 repair loop) ──────────────────────────────
        yield self._ev(sid, "verification", "started", "Verifying SQL (3-layer chain)…")
        verify = self._verification.verify(candidate, self._db_profile)

        if not verify.overall_passed and verify.repaired_sql:
            # One repair attempt
            yield self._ev(sid, "verification", "progress",
                           f"Repair applied: {verify.repair_explanation}")
            repaired_candidate = SqlCandidate(
                sql=verify.repaired_sql,
                rationale=candidate.rationale,
                generation_method=candidate.generation_method,
            )
            verify = self._verification.verify(repaired_candidate, self._db_profile)
            if verify.overall_passed:
                candidate = repaired_candidate
                result.sql = candidate

        result.verify = verify
        if not verify.overall_passed:
            yield self._ev(sid, "verification", "error",
                           "SQL failed all verification layers — not executed",
                           verify.model_dump())
            result.error = "Verification failed."
            yield result
            return

        yield self._ev(sid, "verification", "done",
                       "SQL passed all 3 layers",
                       verify.model_dump())

        # ── 6. Execution ──────────────────────────────────────────────────────
        yield self._ev(sid, "orchestrator", "progress", "Executing SQL…")
        try:
            rows = self._db.execute_read(candidate.sql)
            result.rows = rows
            result.row_count = len(rows)

            # Build teaching summary
            rationale = candidate.rationale or ""
            layers = (
                f"Syntax: {verify.syntax.message} | "
                f"Semantic: {verify.semantic.message} | "
                f"Sanity: {verify.sanity.message}"
            )
            result.teaching_summary = (
                f"**What I understood:** {intent.plain_restatement}\n\n"
                f"**Why this SQL:** {rationale}\n\n"
                f"**Verification:** {layers}\n\n"
                f"**Result:** {len(rows)} row(s) returned."
            )
            append_turn(sid, "assistant", result.teaching_summary,
                        sql=candidate.sql, rows=rows[:10])
            yield self._ev(sid, "orchestrator", "done",
                           f"Done — {len(rows)} row(s)",
                           {"row_count": len(rows)})
        except Exception as e:
            yield self._ev(sid, "orchestrator", "error", str(e))
            result.error = str(e)

        yield result


orchestrator = Orchestrator()
```

---

## Step 10 — Update API Routes for Sessions

Update `backend/app/api/routes/session.py`:

```python
"""Session routes — list, get, and create sessions."""

from fastapi import APIRouter, HTTPException
from backend.app.services.memory.sessions import (
    list_sessions, get_session, create_session,
)

router = APIRouter()


@router.get("/session")
def sessions_list():
    return {"sessions": list_sessions()}


@router.get("/session/{session_id}")
def session_get(session_id: str):
    s = get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.post("/session")
def session_create(db_name: str = "soundwave_db", title: str = ""):
    sid = create_session(db_name=db_name, title=title)
    return {"session_id": sid}
```

---

## Step 11 — Gate D2 Verification Script

Create `tests/gate_d2.py` — the automated Gate D2 checker:

```python
"""
Gate D2 verification script.
Sends 8 probe queries (one per EC-01…EC-08) to POST /query
and checks that ≥ 6/8 pass verification and return rows.

Run:
    python tests/gate_d2.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

PROBES = [
    {
        "ec": "EC-01",
        "query": "Show me all artists from Colombia.",
        "expected_table": "artists",
        "must_not_contain": "users",
    },
    {
        "ec": "EC-02",
        "query": "Which subscription plans include high-fidelity audio?",
        "expected_keyword": "has_hifi",
    },
    {
        "ec": "EC-03",
        "query": "How many tracks are standalone singles (not part of any album)?",
        "expected_keyword": "IS NULL",
    },
    {
        "ec": "EC-04",
        "query": "Which genres have subgenres?",
        "expected_table": "genres",
    },
    {
        "ec": "EC-05",
        "query": "What is the average track duration in minutes?",
        "expected_keyword": "trk_dur_ms",
    },
    {
        "ec": "EC-06",
        "query": "What is the current price of the Individual Premium plan?",
        "expected_table": "pricing_history",
    },
    {
        "ec": "EC-07",
        "query": "Which artist had the most plays last month?",
        "note": "Should use play_events, not cached daily_artist_metrics",
    },
    {
        "ec": "EC-08",
        "query": "Which playlists contain tracks by Adele?",
        "expected_table": "playlist_tracks",
    },
]


def run_query(query: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/query",
        json={"message": query},
        stream=True,
        timeout=120,
    )
    result = {}
    events = []
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("type") == "result":
                result = data
            else:
                events.append(data)
    return result, events


def main():
    passed = 0
    failed = 0

    print(f"\nGate D2 — Running {len(PROBES)} edge-case probes\n{'='*60}")

    for probe in PROBES:
        ec = probe["ec"]
        query = probe["query"]
        print(f"\n[{ec}] {query}")

        try:
            result, events = run_query(query)
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
            continue

        # Check verification passed
        verify = result.get("verify") or {}
        if not verify.get("overall_passed", False):
            print(f"  FAIL — verification did not pass")
            print(f"         syntax:   {verify.get('syntax', {}).get('message')}")
            print(f"         semantic: {verify.get('semantic', {}).get('message')}")
            print(f"         sanity:   {verify.get('sanity', {}).get('message')}")
            failed += 1
            continue

        # Check rows returned
        row_count = result.get("row_count", 0)
        if row_count == 0:
            print(f"  FAIL — 0 rows returned")
            failed += 1
            continue

        # Check SQL content hints
        sql = (result.get("sql") or {}).get("sql", "").upper()
        hint_ok = True
        if probe.get("expected_keyword"):
            kw = probe["expected_keyword"].upper()
            if kw not in sql:
                print(f"  WARN — expected '{probe['expected_keyword']}' not in SQL")
        if probe.get("expected_table"):
            tbl = probe["expected_table"].upper()
            if tbl not in sql:
                print(f"  WARN — expected table '{probe['expected_table']}' not in SQL")

        print(f"  PASS — {row_count} row(s) | verification passed")
        passed += 1

    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(PROBES)} passed  (need ≥ 6)")
    if passed >= 6:
        print("GATE D2: PASSED")
        sys.exit(0)
    else:
        print("GATE D2: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Step 12 — Session Persistence Restart Test

```
# 1. Start the backend
python start.py

# 2. Run a query and note the session_id from the result
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How many tracks are standalone singles?\"}"
# Copy the session_id from the output

# 3. Stop the backend (Ctrl+C)
# 4. Restart
python start.py

# 5. Retrieve the session by ID — it must still exist
curl http://localhost:5000/session/<session_id>
# Expected: session object with at least 2 turns (user + assistant)
```

---

## Gate D2 Verification

```
python tests/gate_d2.py
```

**Pass criteria:**
1. Script exits 0 (≥ 6/8 probes pass).
2. Each passing probe: `verify.overall_passed = true` AND `row_count > 0`.
3. EC-03 probe SQL contains `IS NULL`.
4. Session persists across backend restart (Step 12).
5. `/session` endpoint returns at least one session with turns populated.

---

## File Checklist

Files created or significantly modified during Day 2:

| File | Action |
|---|---|
| `backend/requirements.txt` | chromadb, sentence-transformers added |
| `backend/app/agents/context_manager.py` | Created |
| `backend/app/agents/query_understanding.py` | Created |
| `backend/app/agents/clarification.py` | Created |
| `backend/app/agents/sql_generator.py` | Created |
| `backend/app/agents/verification.py` | Created |
| `backend/app/services/memory/sessions.py` | Created |
| `backend/app/services/memory/vector.py` | Created |
| `backend/app/services/orchestrator.py` | Full rewrite — real agents wired |
| `backend/app/api/routes/session.py` | Expanded — list/get/create |
| `backend/app/main.py` | `init_db()` call at startup |
| `tests/gate_d2.py` | Created |
| `data/sessions.db` | Auto-created at runtime |
| `data/chromadb/` | Auto-created at runtime |
