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
- time_range: any time constraint (or null). NEVER invent a number the user did not say:
  a vague window like "the last months" or "recently" must NOT become "last 3 months" —
  add an ambiguity flag instead and leave time_range as the user's literal words.
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


# Vague-time safety net: a time constraint with no concrete number or date ("the last
# months", "past few weeks", "recently"). Small local LLMs tend to silently invent a
# number ("last 3 months") instead of flagging the vagueness, so — same regex-first
# discipline as above — this is caught deterministically and forced into ambiguity_flags,
# which routes the pipeline into the clarification branch before any SQL is generated.
VAGUE_TIME_FLAG_PREFIX = "vague time range:"

_NUMBER_WORD = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"twenty|thirty|sixty|ninety)"
)

# "last months", "past few weeks", "recent days" — plural unit with no number in front.
# The lookahead rejects "last 3 months"; the plural-only unit group rejects "last month"
# (singular = concretely one month).
_VAGUE_TIME_UNIT_RE = re.compile(
    rf"\b(?:last|past|previous|recent)\s+"
    rf"(?!{_NUMBER_WORD}\b)"
    rf"(?:(?:few|couple(?:\s+of)?|several)\s+)?"
    rf"(months|weeks|days|years)\b",
    re.IGNORECASE,
)

# Bare vague time words with no unit at all. These only count as vague when they are the
# query's ONLY time constraint (see _CONCRETE_TIME_RE below).
_VAGUE_TIME_BARE_RE = re.compile(
    r"\b(recently|lately|these\s+days|not\s+long\s+ago|in\s+recent\s+times)\b",
    re.IGNORECASE,
)

# Concrete time signals that make a bare vague word redundant rather than ambiguous
# (e.g. "recently, since January 2026" — the explicit part wins, no clarification).
_CONCRETE_TIME_RE = re.compile(
    rf"\b(?:last|past|previous)\s+{_NUMBER_WORD}\s+(?:day|week|month|year)s?\b"
    r"|\b(?:last|past|previous|this|current)\s+(?:day|week|month|year|quarter)\b"
    r"|\b(?:yesterday|today)\b"
    r"|\b(?:since|until|before|after)\s+\S"
    r"|\b(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b"
    r"|\b\d{4}\b|\b\d{1,2}[/-]\d{1,2}\b",
    re.IGNORECASE,
)


def _detect_vague_time_range(query: str) -> tuple[str, str] | None:
    """Return (matched phrase, unit) when the query constrains by time without a
    concrete number or date, else None. Unit defaults to "months" for bare vague
    words like "recently" that name no unit themselves."""
    match = _VAGUE_TIME_UNIT_RE.search(query)
    if match:
        return match.group(0).strip(), match.group(1).lower()
    match = _VAGUE_TIME_BARE_RE.search(query)
    if match and not _CONCRETE_TIME_RE.search(query):
        return match.group(0).strip(), "months"
    return None


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

        # Vague-time safety net (see _detect_vague_time_range). Only the [Current] segment
        # is inspected: when the orchestrator injects [History], a vague phrase in an
        # already-clarified earlier turn must not re-trigger the clarification loop.
        ambiguity_flags: list[str] = list(data.get("ambiguity_flags", []) or [])
        current_query = query.split("[Current]", 1)[-1] if "[Current]" in query else query
        vague = _detect_vague_time_range(current_query)
        if vague:
            phrase, unit = vague
            already_flagged = any(
                phrase.lower() in f.lower() or "time" in f.lower() for f in ambiguity_flags
            )
            if not already_flagged:
                ambiguity_flags.append(
                    f"{VAGUE_TIME_FLAG_PREFIX} '{phrase}' does not specify how many {unit}"
                )

        return Intent(
            raw_query=query,
            entities=entities,
            metrics=data.get("metrics", []),
            filters=data.get("filters", []),
            requested_fields=requested_fields,
            time_range=data.get("time_range"),
            ambiguity_flags=ambiguity_flags,
            plain_restatement=plain_restatement,
        )
