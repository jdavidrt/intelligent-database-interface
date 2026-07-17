"""gretelai/synthetic_text_to_sql filtering + formatting for the sql_generator mix.

Dependency-light on purpose (only sqlglot) so the Colab notebook can import it
without pulling the backend stack (chromadb, sentence-transformers, ...). The
system prompt is NOT imported from the backend — the notebook reads it off the
first record of the soundwave train JSONL, guaranteeing both sources share the
exact same system message.
"""

from __future__ import annotations

import random

import sqlglot
from sqlglot import exp

GRETEL_DATASET = "gretelai/synthetic_text_to_sql"

# Skip 'basic SQL' — the 3B base model already handles it; we mix medium/hard
# shapes so soundwave specialization doesn't erode general SQL competence.
GRETEL_KEEP_COMPLEXITY = {
    "aggregation",
    "single join",
    "multiple_joins",
    "subqueries",
    "window functions",
    "set operations",
}


def gretel_keep(record: dict) -> bool:
    sql = (record.get("sql") or "").strip()
    if not sql.upper().startswith("SELECT"):
        return False
    if ";" in sql.rstrip().rstrip(";"):
        return False  # multi-statement
    if record.get("sql_complexity") not in GRETEL_KEEP_COMPLEXITY:
        return False
    return bool(record.get("sql_context")) and bool(record.get("sql_prompt"))


def format_gretel_example(record: dict, system_prompt: str) -> dict:
    """Serialize a gretel row into the exact runtime sql_generator prompt shape.

    The DDL plays the role of the schema summary; the retrieval block is emulated
    with per-table 'Table: X. Columns: ...' passages, matching what
    backend/app/services/memory/vector.py embeds for the live database.
    """
    ddl = record["sql_context"].strip()
    passages: list[str] = []
    try:
        for stmt in sqlglot.parse(ddl):
            if isinstance(stmt, exp.Create) and isinstance(stmt.this, exp.Schema):
                tname = stmt.this.this.name
                cols = ", ".join(
                    d.name for d in stmt.this.expressions if isinstance(d, exp.ColumnDef)
                )
                passages.append(f"Table: {tname}. Columns: {cols}.")
    except Exception:
        pass
    context_str = "\n".join(passages) if passages else ddl

    nl = record["sql_prompt"].strip()
    user = "\n\n".join(
        [
            f"Schema:\n{ddl}",
            f"Relevant context:\n{context_str}",
            f"User intent: {nl}",
            f"Original query: {nl}",
        ]
    )
    rationale = (record.get("sql_explanation") or "Direct translation of the request.").strip()
    target = f"### Rationale\n{rationale}\n\n### SQL\n```sql\n{record['sql'].strip()}\n```"
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
            {"role": "assistant", "content": target},
        ],
        "meta": {"id": f"gretel-{record.get('id', '?')}", "ec": "external", "split": "train"},
    }


def build_gretel_mix(rows, n: int, system_prompt: str, seed: int = 42) -> list[dict]:
    """Filter an iterable of gretel rows and sample n formatted examples."""
    kept = [r for r in rows if gretel_keep(r)]
    random.Random(seed).shuffle(kept)
    return [format_gretel_example(r, system_prompt) for r in kept[:n]]
