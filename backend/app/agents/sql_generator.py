"""SQL Generator — NL->SQL with rationale, grounded in DBProfile + ChromaDB context."""

from __future__ import annotations

import re

from backend.app.models.envelope import DBProfile, Intent, SqlCandidate
from backend.app.services import clock, temporal
from backend.app.services.llm_service import llm_service
from backend.app.services.memory.vector import query_context

SYSTEM_PROMPT = """\
You are the SQL Generator module of IDI, an NL2SQL assistant for a MySQL database.

Rules:
1. Generate a single SELECT statement only. Never INSERT/UPDATE/DELETE/DROP.
2. Always qualify column names with table names when ambiguity is possible.
3. Use the schema context and DBProfile to resolve table and column names.
4. The "Tables (complete list)" line in the schema is exhaustive: any name not on
   it does not exist as a table. Columns are never tables — never JOIN a column name.
4b. The "Join paths (complete list)" line is equally exhaustive: every JOIN's ON
   clause must be one of the listed equalities, copied verbatim (aliases aside).
   Never invent a join key — if two tables have no listed path, join them through
   an intermediate table that does. Only join tables the question actually needs.
5. Relative time windows ("last 8 months", "past 2 weeks", "this year") MUST be
   computed from the current date with date arithmetic — e.g.
   `col >= DATE_SUB(CURDATE(), INTERVAL 8 MONTH)` or `YEAR(col) = YEAR(CURDATE())`.
   NEVER substitute a hardcoded year or date literal (e.g. `YEAR(col) = 2024`) for a
   relative window: you do not know what "now" is unless you anchor to CURDATE()/NOW().
   The user prompt states the current date — use it only to sanity-check, still emit
   CURDATE()-anchored SQL so the query stays correct tomorrow.
5b. Unit fidelity (STRICT): the INTERVAL must carry the question's own number and
   unit. "last 7 months" → `INTERVAL 7 MONTH` — never `INTERVAL 7 YEAR`, never
   `YEAR(col) >= YEAR(CURDATE()) - 7` (that is a 7-YEAR filter), never a converted
   unit. Months are never expressible in days or via YEAR() arithmetic.
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
    # Closed table list: small models respect a short explicit enumeration far
    # better than one implied by the per-table detail below (hallucinated-table guard).
    lines.append(
        "Tables (complete list — a name not listed here is NOT a table): "
        + ", ".join(t.name for t in profile.tables)
    )
    for t in profile.tables:
        cols = ", ".join(
            f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''}"
            + (", PK" if c.is_primary_key else "")
            + (f", FK->{c.references}" if c.is_foreign_key and c.references else "")
            + ")"
            for c in t.columns
        )
        lines.append(f"  {t.name}: {cols}")
    # Closed join map: every legal JOIN condition, spelled out. Small models
    # hallucinate join keys (e.g. artists.user_id) when left to guess them.
    if profile.relationship_edges:
        lines.append(
            "Join paths (complete list — every JOIN's ON clause MUST be one of these "
            "equalities; a join key not listed here does NOT exist): "
            + "; ".join(f"{src} = {tgt}" for src, tgt in profile.relationship_edges)
        )
    if profile.glossary:
        lines.append("Glossary: " + ", ".join(f"{k}={v}" for k, v in profile.glossary.items()))
    if profile.coded_value_maps:
        for col, mapping in profile.coded_value_maps.items():
            lines.append(
                f"Coded values for {col}: " + ", ".join(f"{k}->{v}" for k, v in mapping.items())
            )
    if profile.source_of_truth:
        lines.append(
            "Source-of-truth notes (ambiguous concept -> canonical source): "
            + "; ".join(f"{k} -> {v}" for k, v in profile.source_of_truth.items())
        )
    return "\n".join(lines)


class SQLGenerator:
    def __init__(self) -> None:
        self.last_meta: dict | None = None

    def generate(
        self, intent: Intent, profile: DBProfile, feedback: str | None = None
    ) -> SqlCandidate:
        schema_summary = _build_schema_summary(profile)
        context_passages = query_context(intent.raw_query, n_results=4)
        context_str = "\n".join(context_passages)

        intent_lines = [
            f"Schema:\n{schema_summary}",
            f"Relevant context:\n{context_str}",
            clock.date_context(),
            f"User intent: {intent.plain_restatement}",
            f"Original query: {intent.raw_query}",
        ]
        if intent.time_range:
            window = temporal.extract_relative_window(f"{intent.time_range} {intent.raw_query}")
            if window:
                n, unit = window
                intent_lines.append(
                    f"Time constraint (STRICT): '{intent.time_range}' is a rolling "
                    f"{n}-{unit} window. The date filter MUST be written exactly as:\n"
                    f"  {temporal.required_predicate(n, unit)}\n"
                    f"Same number ({n}), same unit ({unit.upper()}) — never convert "
                    f"{unit}s to a different unit, and never use YEAR() arithmetic "
                    f"(e.g. YEAR(col) >= YEAR(CURDATE()) - {n}) to express a "
                    f"{unit} window; the verification layer rejects any other shape."
                )
            else:
                intent_lines.append(
                    f"Time constraint (user's words): {intent.time_range} — if this is a "
                    "relative window, anchor it to CURDATE() with DATE_SUB(...), never a "
                    "hardcoded year or date literal."
                )
        if intent.requested_fields:
            intent_lines.append(
                "Explicitly requested output fields (MUST appear in the SELECT list, "
                f"resolved against the schema above): {', '.join(intent.requested_fields)}"
            )
        if intent.entities:
            intent_lines.append(f"Entities referenced: {', '.join(intent.entities)}")
        if intent.filters:
            intent_lines.append(f"Filters: {', '.join(intent.filters)}")
        if feedback:
            valid_tables = ", ".join(t.name for t in profile.tables)
            intent_lines.append(
                "IMPORTANT — your previous attempt was rejected by the verification "
                f"layer:\n{feedback}\n"
                "Generate a corrected query. Every table and column you reference must "
                "appear in the schema above — do not repeat the rejected pattern. "
                f"The ONLY valid tables are: {valid_tables}. Any other name is a column "
                "or does not exist. If the rejection names a column, re-derive every "
                "JOIN's ON clause from the 'Join paths (complete list)' line — the "
                "rejected join key was invented, not real."
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(intent_lines)},
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
