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
- requested_fields: specific output columns/fields the user explicitly named as what to
  return (e.g. "give me the names", "show me their emails" -> ["names"] / ["emails"]).
  Empty list if the user never named a specific output field. Never drop one of these —
  a value in requested_fields is a hard requirement on the final SELECT list, not a
  suggestion.
- time_range: any time constraint (or null)
- ambiguity_flags: list of ambiguities (e.g. "column 'name' exists in multiple tables")
- plain_restatement: one sentence restating what the user is asking. If requested_fields
  is non-empty, the restatement MUST name those fields explicitly (do not generalize them
  away into a vague "details" or "info").

Respond with ONLY valid JSON matching this schema:
{
  "entities": [...],
  "metrics": [...],
  "filters": [...],
  "requested_fields": [...],
  "time_range": null,
  "ambiguity_flags": [...],
  "plain_restatement": "..."
}
"""

# Safety net: small local LLMs sometimes drop a trailing "give me the X" clause when
# restating the question in prose. This regex catches the common phrasings deterministically
# so a requested output field is never lost purely to model inattention (same pattern as
# clarification.py's MetaQuestionFilter: regex-first, LLM is not the only line of defense).
_REQUESTED_FIELD_TRIGGER_RE = re.compile(
    r"\b(?:give me|show me|i(?:'d| would)? like|i want|just want|return|list)\s+"
    r"(?:the|their|its|only|just)*\s*"
    r"([a-z][a-z\s]*?)\s*(?:please)?\s*[.?!]?\s*$",
    re.IGNORECASE,
)


def _extract_requested_fields(query: str) -> list[str]:
    match = _REQUESTED_FIELD_TRIGGER_RE.search(query)
    if not match:
        return []
    phrase = match.group(1).strip().lower()
    if not phrase:
        return []
    parts = re.split(r"\s*(?:,|\band\b)\s*", phrase)
    return [p.strip() for p in parts if p.strip()]


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

        # Merge LLM-extracted requested_fields with the regex safety net (dedup, case-insensitive).
        # The regex is deliberately greedy when a query has no separate trailing clause (e.g.
        # "show me the emails of banned users" captures "emails of banned users" whole), so a
        # substring match against something the LLM already extracted counts as a duplicate too.
        requested_fields: list[str] = list(data.get("requested_fields", []) or [])
        seen = {f.lower() for f in requested_fields}
        for field in _extract_requested_fields(query):
            fl = field.lower()
            if any(fl == s or fl in s or s in fl for s in seen):
                continue
            requested_fields.append(field)
            seen.add(fl)

        # Requested fields are also entities (columns the user cares about).
        entities: list[str] = list(data.get("entities", []) or [])
        entity_seen = {e.lower() for e in entities}
        for field in requested_fields:
            if field.lower() not in entity_seen:
                entities.append(field)
                entity_seen.add(field.lower())

        # Fail-safe: if the model's restatement dropped a requested field, append it rather
        # than silently losing it — this is the text the SQL Generator and the didactic UI both read.
        plain_restatement = data.get("plain_restatement", f"You asked: '{query}'")
        missing = [f for f in requested_fields if f.lower() not in plain_restatement.lower()]
        if missing:
            plain_restatement = plain_restatement.rstrip(".") + f" — returning: {', '.join(missing)}."

        return Intent(
            raw_query=query,
            entities=entities,
            metrics=data.get("metrics", []),
            filters=data.get("filters", []),
            requested_fields=requested_fields,
            time_range=data.get("time_range"),
            ambiguity_flags=data.get("ambiguity_flags", []),
            plain_restatement=plain_restatement,
        )
