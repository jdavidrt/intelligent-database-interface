# Services (Day 1 target)

Core service layer:
- `llm_service.py` — llama.cpp client, LoRA hot-swap, base-model fallback. Wraps
  the migrated `app/main.py:/chat` loop as the SQL-generation fallback.
- `orchestrator.py` — 7-agent workflow routing + per-step `AgentEvent`s.
- `sql_executor.py` — read-only execution via `DBConnector` (forced `LIMIT`).
- `db/connector.py`, `db/mysql_connector.py` — thin DB seam (soundwave/MySQL).
- `memory/sessions.py` (SQLite), `memory/vector.py` (ChromaDB).
