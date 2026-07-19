# Services (Day 1 target)

Core service layer:
- `llm_service.py` — llama.cpp client, LoRA hot-swap, base-model fallback. Wraps
  the migrated `app/main.py:/chat` loop as the SQL-generation fallback.
- `orchestrator.py` — 7-agent workflow routing + per-step `AgentEvent`s.
- `sql_executor.py` — read-only execution via `DBConnector` (forced `LIMIT`).
- `db/connector.py`, `db/file_connector.py`, `db/mysql_connector.py` — thin DB seam (file/MySQL), parameterized by `db_name`.
- `db/discovery.py` — scans `databases/` for valid DB folders (dynamic multi-database listing).
- `db/join_graph.py` — deterministic FK-path resolution (closed join vocabulary): column
  equivalence classes make transitive joins legal, junction-preferred shortest paths encode the
  EC-08 bridge rule; feeds the SQL Generator's plan step and the verifier's rule-4b enforcement.
- `memory/sessions.py` (SQLite), `memory/vector.py` (ChromaDB).
