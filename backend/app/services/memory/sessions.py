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


def set_title_if_default(session_id: str, title: str) -> None:
    """Set the session title only if it's still the auto-generated default."""
    clean = title.strip()[:60]
    if not clean:
        return
    with _conn() as con:
        con.execute(
            "UPDATE sessions SET title = ? "
            "WHERE session_id = ? AND (title IS NULL OR title = '' OR title LIKE 'Session %')",
            (clean, session_id),
        )


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
