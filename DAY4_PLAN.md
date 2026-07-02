# Day 4 — Real DB Connection & Hardening
## IDI Implementation Plan (v2)

**Goal:** The physical database arrives last — and nothing above the `DBConnector` seam notices. Then make the whole build reproducible.

**Gate D4:** EC suite green on MySQL with results identical to the file-connector run; `IDI_CONNECTOR=file` still boots with zero DB setup; one-command bring-up works; verification never lets malformed SQL execute.

**Pre-condition:** Gate D3 passed — registry, A/B report, tests, and lint all in place.

---

## Step 1 — MySQL Setup & Soundwave Load

`[v1 → legacydocs/DAY1_PLAN_v1.md Step 4]` verbatim: install MySQL Community Server 8.x, create `soundwave_db` (utf8mb4), `SOURCE` the three soundwave SQL files, verify 19 tables and seed counts.

Add the MySQL fields back into `backend/app/config.py` (they were dropped in v2 Day 1 Step 2) and extend `.env`:

```
IDI_CONNECTOR=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=soundwave_db
DB_USER=root
DB_PASSWORD=your_mysql_root_password
```

Add `mysql-connector-python>=9.0.0` to `backend/requirements.txt` and install.

---

## Step 2 — `MySQLConnector`

`[v1 → legacydocs/DAY1_PLAN_v1.md Step 5]` verbatim: `backend/app/services/db/mysql_connector.py` — `information_schema` introspection, read-only `execute_read` with LIMIT injection, `EXPLAIN` probe.

One v2 addition: `execute_read` does **not** transpile (agents already emit MySQL) — the transpile-at-the-boundary logic stays exclusive to the file connector.

---

## Step 3 — Wire the Factory

Complete `get_connector()` in `backend/app/services/db/connector.py` (the Day 1 factory left the mysql branch raising `NotImplementedError`):

```python
def get_connector():
    from backend.app.config import settings
    if settings.connector == "mysql":
        from .mysql_connector import MySQLConnector
        return MySQLConnector()
    from .file_connector import SoundwaveFileConnector
    return SoundwaveFileConnector()
```

No agent, orchestrator, route, or frontend file changes. If any does, the seam leaked — fix the seam, not the caller.

---

## Step 4 — Parity Check (File vs MySQL)

Create `tests/parity_check.py`:

- Run the EC suite twice: `IDI_CONNECTOR=file`, then `IDI_CONNECTOR=mysql` (backend restart between runs).
- Compare per-probe: verification verdicts and returned rows (order-insensitive).
- Output: `data/benchmarks/parity_<date>.json`. Any divergence is a transpile bug or an introspection gap — file an issue against the file connector, since MySQL is now ground truth.

Also re-run `tests/evaluate.py` on MySQL and record both engines' latency side by side.

---

## Step 5 — DBProfileForm Write Path (Characterization Survey)

Now that a genuinely foreign database can connect, wire the Day 2 survey form's write path: `POST /db/profile/survey` merges glossary / coded values / source-of-truth / sensitivity into the persisted `DBProfile` and re-embeds into ChromaDB. This completes MASTERPLAN §6 for arbitrary MySQL databases.

---

## Step 6 — Docker Compose & RUN_GUIDE

`[v1 → legacydocs/DAY4_PLAN_v1.md Steps 8–9]` carry over with the compose file gaining the connector flag: `IDI_CONNECTOR=mysql` in the backend service env, MySQL service with the soundwave SQL mounted as init scripts. Document both modes in `RUN_GUIDE.md`:

- **Zero-setup demo**: `IDI_CONNECTOR=file` + `python start.py` (no Docker, no MySQL).
- **Full stack**: `docker-compose up`.

---

## Step 7 — Skeptical Review Pass (All Gates, Both Connectors)

`[v1 → legacydocs/DAY4_PLAN_v1.md Step 10]` retargeted:

1. Gate D1 script on `file` connector.
2. Gate D2 browser walk-through on `mysql` connector.
3. Gate D3: registry fallback still graceful; A/B report reproducible.
4. Gate D4: parity green, compose bring-up, malformed-SQL guard test (`DROP TABLE` attempt must never reach execution on either connector).
5. VRAM check under load < 3.5 GB.

---

## Post-Sprint Pointer — LoRA Training

When training begins (Colab + Unsloth per MASTERPLAN §8): `[v1 → legacydocs/DAY4_PLAN_v1.md Steps 1–3]` contain the complete GGUF pull + `/lora-adapters` hot-swap wiring + per-agent A/B code. Flip each agent's `registry.json` entry from `prompt:` to `gguf:` as its adapter beats the Day 3 baseline.

---

## File Checklist

| File | Action |
|---|---|
| `backend/requirements.txt` | + mysql-connector-python |
| `backend/app/config.py` | MySQL fields restored |
| `backend/app/services/db/mysql_connector.py` | Created (v1 D1-S5) |
| `backend/app/services/db/connector.py` | Factory completed |
| `backend/app/api/routes/db.py` | Survey write path |
| `tests/parity_check.py` | Created |
| `deployment/docker-compose.yml` | Created (v1 D4-S8 + connector flag) |
| `RUN_GUIDE.md` | Created — both modes documented |
