"""Query Understanding — intent/entity/metric extraction + ambiguity detection."""

from __future__ import annotations

import json
import re

from backend.app.models.envelope import DBProfile, Intent
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
                "content": (f"Schema context:\n{context_str}\n\n" f"User question: {query}"),
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
