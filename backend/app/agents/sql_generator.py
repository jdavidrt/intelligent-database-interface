"""SQL Generator — NL->SQL with rationale, grounded in DBProfile + ChromaDB context."""

from __future__ import annotations

import re

from backend.app.models.envelope import DBProfile, Intent, SqlCandidate
from backend.app.services.llm_service import llm_service
from backend.app.services.memory.vector import query_context

SYSTEM_PROMPT = """\
You are the SQL Generator module of IDI, an NL2SQL assistant for a MySQL database.

Rules:
1. Generate a single SELECT statement only. Never INSERT/UPDATE/DELETE/DROP.
2. Always qualify column names with table names when ambiguity is possible.
3. Use the schema context and DBProfile to resolve table and column names.
4. End the SQL with a semicolon.

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
            f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''})" for c in t.columns
        )
        lines.append(f"  {t.name}: {cols}")
    if profile.glossary:
        lines.append("Glossary: " + ", ".join(f"{k}={v}" for k, v in profile.glossary.items()))
    if profile.coded_value_maps:
        for col, mapping in profile.coded_value_maps.items():
            lines.append(
                f"Coded values for {col}: " + ", ".join(f"{k}->{v}" for k, v in mapping.items())
            )
    return "\n".join(lines)


class SQLGenerator:
    def __init__(self) -> None:
        self.last_meta: dict | None = None

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

        raw, self.last_meta = llm_service.chat_with_meta(messages, temperature=0.2)

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
