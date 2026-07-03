"""Clarification — generates follow-up questions when ambiguity flags fire."""

from __future__ import annotations

from backend.app.models.envelope import Intent
from backend.app.services.llm_service import llm_service

SYSTEM_PROMPT = """\
You are the Clarification module of IDI.
The query understanding module detected the following ambiguities.
Generate one clear, short follow-up question that resolves the most critical ambiguity.
The question should be phrased for a non-technical user.
Respond with ONLY the question text, no preamble.
"""


class Clarification:
    def needs_clarification(self, intent: Intent) -> bool:
        return len(intent.ambiguity_flags) > 0

    def generate_question(self, intent: Intent) -> str:
        if not intent.ambiguity_flags:
            return ""
        flags_str = "\n".join(f"- {f}" for f in intent.ambiguity_flags)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original question: {intent.raw_query}\n" f"Ambiguities:\n{flags_str}"
                ),
            },
        ]
        return llm_service.chat(messages, temperature=0.2).strip()
