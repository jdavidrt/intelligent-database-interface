# Day 1 — The Agentic Core (DB-less)
## IDI Implementation Plan (v2)

> **✅ COMPLETE — 2026-07-02. Gate D1 PASSED (6/8).** The seven-agent pipeline runs end-to-end over `/query`, fed by the `soundwave/` files via `SoundwaveFileConnector`. EC-07/EC-08 were correctly blocked at the syntax-verification layer (fail-safe working as designed). As a follow-on, the frozen `sandbox/` was **deleted** and the project fully detached from it — model relocated to `models/`, `llama-server` from winget/PATH, chat frontend repointed to `/query`, and `/chat` + `/benchmark` context sourced from `soundwave/`. Next: **Day 2 — Frontend** (`DAY2_PLAN.md`).
>
> **Post-Day-2 addendum (2026-07-03 — see `MASTERPLAN.md`'s Multi-Database Restructure note):** the `soundwave/` folder moved to `databases/soundwave/`, `SoundwaveFileConnector` was generalized and renamed `FileConnector(db_name)` (glob-based file discovery, no more hardcoded `SCHEMA_FILE`/`DATA_FILE`), `soundwave_dir`/`SOUNDWAVE_DIR` became `databases_dir`/`DATABASES_DIR`, and `get_connector()` now takes a `db_name` argument. The code blocks in Steps 2 and 4 below are kept as-written — they document what Day 1 actually shipped — but no longer match the current source; treat `backend/app/config.py`, `backend/app/services/db/connector.py`, and `backend/app/services/db/file_connector.py` as ground truth.

**Goal:** The full seven-agent pipeline running end-to-end — real verification, persistent memory, auto-exploration — fed entirely by the `soundwave/` files. No MySQL, no DB server, anywhere.

**Gate D1:** `python tests/gate_d1.py` runs 8 probes (EC-01…EC-08) against the file connector; ≥ 6/8 pass verification and return correct rows from the seed data; EC-03 SQL uses `album_id IS NULL`. Sessions survive a backend restart.

**Pre-condition:** Gate D0 passed — `python start.py` brings up llama.cpp + FastAPI + Vite from canonical paths.

**Carry-over convention:** steps marked `[v1 →]` reuse code verbatim from `legacydocs/DAY1_PLAN_v1.md` or `legacydocs/DAY2_PLAN_v1.md`. The only systematic substitution: every `MySQLConnector` import/usage becomes the connector factory (Step 4).

---

## Step 1 — Dependencies

Replace `backend/requirements.txt` (note: **no** `mysql-connector-python` today — it arrives Day 4):

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
requests>=2.31.0
psutil>=5.9.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
sqlglot>=25.0.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
```

```
.venv\Scripts\pip install -r backend/requirements.txt
```

---

## Step 2 — `backend/app/config.py`

`[v1 → DAY1_PLAN_v1.md Step 2]` with two changes:

1. Drop the MySQL fields (`db_host`, `db_port`, `db_user`, `db_password`) — they return on Day 4.
2. Add the connector selector and soundwave paths:

```python
    # Connector selection: "file" (Days 1-3) | "mysql" (Day 4+)
    connector: str = Field(default="file", alias="IDI_CONNECTOR")

    # Soundwave source files (the DB-less context feed)
    soundwave_dir: str = Field(default="soundwave", alias="SOUNDWAVE_DIR")
```

`.env` at repo root (gitignored):

```
IDI_CONNECTOR=file
LLAMA_CPP_SERVER_PORT=7860
BACKEND_PORT=5000
```

---

## Step 3 — Pydantic Envelopes

`[v1 → DAY1_PLAN_v1.md Step 3]` — `backend/app/models/envelope.py` carries over **verbatim**. `DBProfile`, `Intent`, `SqlCandidate`, `VerifyReport`, `AgentEvent`, `QueryResult`. No changes: the envelope was already connector-agnostic.

---

## Step 4 — `DBConnector` Protocol + `SoundwaveFileConnector`

The heart of the v2 replan. `backend/app/services/db/connector.py` carries over from `[v1 → DAY1_PLAN_v1.md Step 5]` (the protocol is unchanged). Add a factory at the bottom:

```python
def get_connector():
    """Return the active DBConnector implementation per settings.connector."""
    from backend.app.config import settings
    if settings.connector == "mysql":
        # Day 4: from .mysql_connector import MySQLConnector; return MySQLConnector()
        raise NotImplementedError("MySQLConnector arrives on Day 4.")
    from .file_connector import SoundwaveFileConnector
    return SoundwaveFileConnector()
```

Create `backend/app/services/db/file_connector.py`:

```python
"""SoundwaveFileConnector — in-memory SQLite built from the soundwave/ SQL files.

Implements the DBConnector protocol without any database server:
- Schema and seed data are transpiled MySQL -> SQLite via sqlglot at startup.
- introspect() builds the DBProfile from the parsed schema AST (not from a live DB).
- execute_read() returns real rows from the seed data, read-only, forced LIMIT.
"""

from __future__ import annotations
import os
import re
import sqlite3
import threading
from typing import Any

import sqlglot
from sqlglot import exp

from backend.app.config import settings
from backend.app.models.envelope import DBProfile, TableInfo, ColumnInfo


class SoundwaveFileConnector:
    SCHEMA_FILE = "01_soundwave_schema.sql"
    DATA_FILE = "02_soundwave_data.sql"

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._sw_dir = os.path.join(settings.repo_root, settings.soundwave_dir)
        self._schema_asts: list[exp.Expression] = []

    # -- lifecycle -------------------------------------------------------------

    def connect(self) -> None:
        """Build the in-memory DB once: transpile schema + data, execute both."""
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._load_sql_file(self.SCHEMA_FILE, keep_asts=True)
        self._load_sql_file(self.DATA_FILE)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
        self._conn = None

    def _load_sql_file(self, filename: str, keep_asts: bool = False) -> None:
        path = os.path.join(self._sw_dir, filename)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        # Strip MySQL-only directives sqlglot does not need to see
        raw = re.sub(r"(?im)^\s*(SET|USE|CREATE\s+DATABASE|LOCK|UNLOCK)\b.*?;", "", raw)
        statements = sqlglot.parse(raw, dialect="mysql")
        cur = self._conn.cursor()
        for stmt in statements:
            if stmt is None:
                continue
            if keep_asts and isinstance(stmt, exp.Create):
                self._schema_asts.append(stmt)
            try:
                cur.execute(stmt.sql(dialect="sqlite"))
            except sqlite3.Error as e:
                # Log and continue: FK pragmas / engine clauses may not translate.
                print(f"[FileConnector] skipped statement in {filename}: {e}")
        self._conn.commit()
        cur.close()

    # -- introspection (from the parsed schema, not the live DB) ----------------

    def introspect(self) -> DBProfile:
        self.connect()
        tables: list[TableInfo] = []
        edges: list[tuple[str, str]] = []

        for create in self._schema_asts:
            tname = create.this.this.name if isinstance(create.this, exp.Schema) else create.this.name
            schema = create.this if isinstance(create.this, exp.Schema) else None
            columns: list[ColumnInfo] = []
            pks: set[str] = set()
            fks: dict[str, str] = {}

            if schema:
                for defn in schema.expressions:
                    if isinstance(defn, exp.ColumnDef):
                        constraints = [c.kind for c in defn.constraints]
                        if any(isinstance(k, exp.PrimaryKeyColumnConstraint) for k in constraints):
                            pks.add(defn.name)
                        columns.append(ColumnInfo(
                            name=defn.name,
                            data_type=defn.args["kind"].sql(dialect="mysql") if defn.args.get("kind") else "unknown",
                            is_nullable=not any(isinstance(k, exp.NotNullColumnConstraint) for k in constraints),
                        ))
                    elif isinstance(defn, exp.PrimaryKey):
                        pks.update(c.name for c in defn.expressions)
                    elif isinstance(defn, exp.ForeignKey):
                        src_cols = [c.name for c in defn.expressions]
                        ref = defn.args.get("reference")
                        if ref:
                            ref_table = ref.this.this.name
                            ref_cols = [c.name for c in ref.this.expressions]
                            for s, r in zip(src_cols, ref_cols):
                                fks[s] = f"{ref_table}.{r}"
                                edges.append((f"{tname}.{s}", f"{ref_table}.{r}"))

            for col in columns:
                col.is_primary_key = col.name in pks
                if col.name in fks:
                    col.is_foreign_key = True
                    col.references = fks[col.name]

            # Real row count from the loaded seed data
            row_count = self._conn.execute(
                f"SELECT COUNT(*) FROM '{tname}'"
            ).fetchone()[0] if self._table_exists(tname) else 0

            tables.append(TableInfo(name=tname, row_count=row_count, columns=columns))

        return DBProfile(db_name="soundwave_db", tables=tables, relationship_edges=edges)

    def _table_exists(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        return row is not None

    # -- read-only execution -----------------------------------------------------

    def execute_read(self, sql: str, limit: int = 200) -> list[dict[str, Any]]:
        self.connect()
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are permitted.")
        # Agents emit MySQL; the engine is SQLite. Transpile at the boundary.
        sql = sqlglot.transpile(sql, read="mysql", write="sqlite")[0]
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            sql = sql.rstrip().rstrip(";") + f" LIMIT {limit}"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def explain(self, sql: str) -> bool:
        """SQLite EXPLAIN QUERY PLAN as the no-execution syntax probe."""
        self.connect()
        try:
            sql_lite = sqlglot.transpile(sql, read="mysql", write="sqlite")[0]
            self._conn.execute(f"EXPLAIN QUERY PLAN {sql_lite.rstrip(';')}")
            return True
        except Exception:
            return False
```

> **Verify immediately** (before building anything on top):
> `python -c "from backend.app.services.db.file_connector import SoundwaveFileConnector as C; c=C(); p=c.introspect(); print(len(p.tables), 'tables'); print(c.execute_read('SELECT COUNT(*) AS n FROM tracks'))"`
> Expected: 19 tables, a real track count. If any statement was skipped during load, inspect the log lines and hand-patch the transpile (frozen files → one-time fix).

---

## Step 5 — `LLMService` with Instruction Hot-Swap

`[v1 → DAY1_PLAN_v1.md Step 6]` is the base. Replace the `load_adapter` stub with the instruction-profile mechanism:

```python
    # -- adapter hot-swap: instruction profiles now, GGUF later ------------------

    def load_adapter(self, adapter_name: str) -> None:
        """Activate the adapter for the next chat() calls.

        v2 semantics: an adapter is an instruction profile at
        backend/app/prompts/<adapter_name>.md. Its content is prepended
        to the system message of subsequent calls. When a real GGUF file
        exists at adapters/<adapter_name>.gguf (post-sprint), this method
        will call llama.cpp /lora-adapters instead - same signature.
        """
        import os
        gguf = os.path.join(settings.repo_root, "adapters", f"{adapter_name}.gguf")
        if os.path.isfile(gguf):
            # Post-sprint branch - wired when trained adapters land.
            print(f"[LLMService] GGUF found for {adapter_name} but hot-swap not wired yet; using instruction profile.")
        path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{adapter_name}.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                self._instruction_profile = f.read()
            self._active_adapter = adapter_name
        else:
            # Fail-safe: missing profile never blocks the pipeline.
            self._instruction_profile = ""
            self._active_adapter = None
            print(f"[LLMService] no profile for '{adapter_name}' - base instructions.")

    def unload_adapter(self) -> None:
        self._instruction_profile = ""
        self._active_adapter = None
```

And in `chat()`, prepend the active profile to the system message before POSTing:

```python
        if getattr(self, "_instruction_profile", ""):
            if messages and messages[0]["role"] == "system":
                messages = [{"role": "system",
                             "content": self._instruction_profile + "\n\n" + messages[0]["content"]}] + messages[1:]
            else:
                messages = [{"role": "system", "content": self._instruction_profile}] + messages
```

Create `backend/app/prompts/` with minimal seed profiles (one paragraph each, expanded on Day 3): `sql_generator.md`, `query_understanding.md`, `verification.md`, `clarification.md`.

---

## Step 6 — Memory: Sessions (SQLite) + Vector Store (ChromaDB)

`[v1 → DAY2_PLAN_v1.md Steps 2–3]` — both files carry over **verbatim**:

- `backend/app/services/memory/sessions.py` (init_db, create_session, append_turn, get_session, list_sessions, get_recent_turns)
- `backend/app/services/memory/vector.py` (embed_db_profile, embed_text, query_context)

Call `init_db()` at FastAPI startup in `main.py`.

---

## Step 7 — Context Manager: Auto-Exploration from `/soundwave`

`[v1 → DAY2_PLAN_v1.md Step 4]` is the base, with the exploration source widened to **all** soundwave files:

- `build_profile()` calls `connector.introspect()` (now the file connector — parsed schema + real seed counts).
- `_apply_soundwave_survey()` carries over (glossary, coded values, source-of-truth from `02_soundwave_context.md`).
- `_embed()` extends to ingest **every** soundwave document into ChromaDB:

```python
    def _embed(self, profile: DBProfile) -> None:
        embed_db_profile(profile)
        sw_dir = os.path.join(settings.repo_root, settings.soundwave_dir)
        for fn in ("02_soundwave_context.md", "03_soundwave_edge_cases.md"):
            path = os.path.join(sw_dir, fn)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    embed_text(f"soundwave::{fn}", f.read(), {"type": "domain_context"})
```

Constructor takes the protocol, not a concrete class: `def __init__(self, connector) -> None` (any `DBConnector`).

---

## Step 8 — The Four LLM Agents

`[v1 → DAY2_PLAN_v1.md Steps 5–8]` carry over with two systematic changes:

1. **Adapter discipline**: each agent's entry point starts with `llm_service.load_adapter("<agent_name>")` so the instruction profile is active for its calls.
2. **Verification agent** takes the protocol (`def __init__(self, connector)`) and its `_layer_syntax` uses `connector.explain()` — which is now SQLite `EXPLAIN QUERY PLAN`. sqlglot still parses with `dialect="mysql"` (agents emit MySQL; the boundary transpiles).

Files: `agents/query_understanding.py`, `agents/clarification.py`, `agents/sql_generator.py`, `agents/verification.py` — otherwise verbatim from v1 Day 2.

---

## Step 9 — Orchestrator (Full Dynamic Routing)

`[v1 → DAY2_PLAN_v1.md Step 9]` carries over with the substitutions:

- `self._db = get_connector()` instead of `MySQLConnector()`.
- Before each LLM agent turn, emit an `AgentEvent` noting the active adapter: payload `{"adapter": llm_service.active_adapter()}` — this is what Gate D3 will later observe.
- Everything else identical: clarification branch, 1 repair loop, teaching summary, session turns.

---

## Step 10 — API Routes + WebSocket

`[v1 → DAY1_PLAN_v1.md Steps 8–10]` (`health.py`, `query.py`, `db.py`, `websocket.py`, `main.py` wiring) + `[v1 → DAY2_PLAN_v1.md Step 10]` (full `session.py`). Carry over verbatim.

---

## Step 11 — Gate D1 Script

`[v1 → DAY2_PLAN_v1.md Step 11]` — the 8-probe EC script carries over as `tests/gate_d1.py` (renamed from `gate_d2.py`; same probes, same ≥ 6/8 threshold).

---

## Gate D1 Verification

```
python start.py          # llama.cpp + backend + frontend; no MySQL anywhere
python tests/gate_d1.py
```

**Pass criteria:**
1. Script exits 0 (≥ 6/8 EC probes pass with `verify.overall_passed = true` and `row_count > 0` from seed data).
2. EC-03 probe SQL contains `IS NULL`.
3. Session persists across backend restart (v1 Day 2 Step 12 procedure).
4. `AgentEvent` stream shows per-agent adapter activation.
5. `tasklist | findstr mysqld` finds nothing — the machine runs no DB server.

---

## File Checklist

| File | Action | Source |
|---|---|---|
| `backend/requirements.txt` | Updated | this plan |
| `backend/app/config.py` | Implemented | v1 D1-S2 modified |
| `backend/app/models/envelope.py` | Created | v1 D1-S3 verbatim |
| `backend/app/services/db/connector.py` | Created + factory | v1 D1-S5 + this plan |
| `backend/app/services/db/file_connector.py` | **Created (new)** | this plan |
| `backend/app/services/llm_service.py` | Created | v1 D1-S6 + instruction hot-swap |
| `backend/app/prompts/*.md` | Created (4 seed profiles) | this plan |
| `backend/app/services/memory/sessions.py` | Created | v1 D2-S2 verbatim |
| `backend/app/services/memory/vector.py` | Created | v1 D2-S3 verbatim |
| `backend/app/agents/context_manager.py` | Created | v1 D2-S4 modified |
| `backend/app/agents/{query_understanding,clarification,sql_generator,verification}.py` | Created | v1 D2-S5…S8 + adapter discipline |
| `backend/app/services/orchestrator.py` | Created | v1 D2-S9 + connector factory |
| `backend/app/api/routes/*.py`, `api/websocket.py` | Created | v1 D1-S8…S10, D2-S10 |
| `tests/gate_d1.py` | Created | v1 D2-S11 renamed |
