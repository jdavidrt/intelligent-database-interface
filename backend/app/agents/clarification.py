"""Clarification — generates follow-up questions when ambiguity flags fire,
and filters out non-SQL "meta" questions about the database or IDI itself."""

from __future__ import annotations

import re

from backend.app.models.envelope import DBProfile, Intent
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


# -- Meta-question filter ---------------------------------------------------------
# Some questions aren't requests for data at all. Three different flavors:
#   - "system" questions: "what is this database about?", "what can you do?" -- about
#     IDI or the connected database itself. These get answered grounded in DBProfile facts.
#   - "SQL-knowledge" questions: "what is a JOIN?", "explain a foreign key" -- general
#     SQL/relational-DB concepts, not about this database's actual data. Answered with
#     general knowledge, not grounded in DBProfile.
#   - "personal/off-topic" questions: "how are you today?", "who are you?", "are you
#     christian?", "how is the weather?" -- directed at the assistant personally, or about
#     real-world facts the assistant has no live access to. These must NEVER be answered by
#     inventing a real-world fact (no fake weather, no fake prices) -- the correct response
#     is a warm, brief redirect back to the database.
# Rather than maintaining an ever-growing blocklist of off-topic phrasings (which is always
# one phrasing behind -- "what's the weather" doesn't catch "how is the weather"), the last
# flavor is caught by an allowlist: a question only reaches intent parsing + SQL generation
# if it's related to the connected DB's domain (string/token match against DBProfile) or is
# a SQL-knowledge question. Anything matching neither is off-topic, deterministically, no
# LLM judgment call needed. Routing any of the three flavors through intent parsing + SQL
# generation would burn a generation cycle on something no SQL could ever answer, so this
# filter catches them before Query Understanding runs and the orchestrator short-circuits
# straight to a plain-language answer.

_SQL_SIGNAL_RE = re.compile(
    r"\b(how many|count|sum|average|avg|total|top|list|show me|group by|order by|"
    r"highest|lowest|most|least|greater than|less than|between)\b"
    # Data-shaped interrogatives: "which genres have subgenres?", "what plans include
    # hi-fi?". These are row questions, not meta questions — without this alternative
    # they fell through to the LLM fallback, which misclassified them as meta (the
    # EC-04 benchmark failure). The lookahead keeps DB-identity/meta phrasings
    # ("which database are we on", "what tables have you got") out of the SQL
    # short-circuit so _META_RE can still catch them below.
    r"|\b(which|what)\s+(?!(?:database|db|schema|table|column)s?\b)\w+\s+"
    r"(?:has|have|had|contains?|includes?)\b"
)

# General SQL/relational-database terminology -- questions about SQL concepts in the
# abstract (e.g. "what is a JOIN?"), not about this connected database's actual data.
_SQL_KNOWLEDGE_RE = re.compile(
    r"\bsql\b|\bquer(y|ies)\b|\bdatabases?\b|\btables?\b|\bcolumns?\b|\bschemas?\b|"
    r"\bjoins?\b|\bforeign key\b|\bprimary key\b|\bindex(es)?\b|\bnormali[sz]"
    r"|\baggregat|\bgroup by\b|\border by\b|\brelational\b|\brows?\b|\brecords?\b|"
    r"\bconstraints?\b|\bstored procedure\b|\btransactions?\b"
)

# Words too common to count as a domain-vocabulary signal on their own.
_STOPWORDS = {
    "the",
    "is",
    "are",
    "a",
    "an",
    "of",
    "in",
    "and",
    "or",
    "to",
    "this",
    "that",
    "for",
    "on",
    "with",
    "as",
    "by",
    "it",
    "its",
    "be",
    "was",
    "were",
    "at",
    "from",
    "you",
    "your",
    "me",
    "my",
    "what",
    "how",
    "who",
    "when",
    "where",
    "why",
    "do",
    "does",
    "can",
    "will",
    "would",
    "there",
    "have",
    "has",
    "had",
}

_WORD_RE = re.compile(r"[a-z]+")


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for w in _WORD_RE.findall(text.lower()):
        if len(w) < 3 or w in _STOPWORDS:
            continue
        tokens.add(w)
        if w.endswith("s") and len(w) > 3:
            tokens.add(w[:-1])
    return tokens


def _domain_vocabulary(profile: DBProfile) -> set[str]:
    """Token set built from every human/schema-supplied name and description in the
    active DBProfile -- table/column names, glossary, coded values, source-of-truth
    notes. Underscores become spaces first so e.g. "trk_dur_ms" tokenizes into
    trk/dur/ms rather than staying one opaque identifier."""
    parts: list[str] = [profile.db_name, profile.domain_description or ""]
    for table in profile.tables:
        parts.append(table.name)
        parts.append(table.description or "")
        for col in table.columns:
            parts.append(col.name)
            if col.glossary_note:
                parts.append(col.glossary_note)
    for k, v in profile.glossary.items():
        parts.append(k)
        parts.append(v)
    for col, mapping in profile.coded_value_maps.items():
        parts.append(col)
        parts.extend(mapping.values())
    for k, v in profile.source_of_truth.items():
        parts.append(k)
        parts.append(v)
    text = " ".join(p.replace("_", " ") for p in parts if p)
    return _tokenize(text)


_META_RE = re.compile(
    r"\bwhat (is|are) (this|the) database\b"
    r"|\bwhat.*(can you|are you able to|are you capable of)\b"
    r"|\bwhat (do|can) you do\b"
    r"|\bwhat kind of questions?\b"
    r"|\bhow (do|does) (this|it) work\b"
    r"|\bwhat.*database.*about\b"
    r"|\bwhat tables?\b"
    r"|\bhelp\b"
    # DB-identity questions about the *currently connected* database. These must be
    # answered from DBProfile facts (its real name/domain), never from generic SQL
    # knowledge -- without these alternatives the bare word "database" would fall
    # through to _SQL_KNOWLEDGE_RE and get a context-less "SELECT DATABASE()" reply.
    r"|\bname of (this|the|our|the current|our current)?\s*(database|db|schema)\b"
    r"|\b(which|what) (database|db|schema)\b"
    r"|\b(current|active|selected|connected|loaded) (database|db|schema)\b"
    r"|\b(database|db|schema) (we('?re| are)|i('?m| am)|you('?re| are)) "
    r"(on|using|connected to|in|working (on|with))\b"
    r"|\bwhat('?s| is) in (this|the) (database|db|schema)\b"
    r"|\bwhat data (do we have|is (in|here|available))\b"
)

# Personal questions directed at the assistant, or out-of-context real-world questions no
# SQL query against this database could ever answer.
_PERSONAL_OFFTOPIC_RE = re.compile(
    r"\bhow are you\b"
    r"|\bhow('s| is) it going\b"
    r"|\bhow (was|is) your day\b"
    r"|\bwho are you\b"
    r"|\bhow (do|does) you work\b"
    r"|\bare you (a |an )?(christian|muslim|jewish|buddhist|atheist|hindu|religious|human|real|"
    r"alive|a robot|an ai|single|married)\b"
    r"|\bwhat('s| is) your (name|favorite|opinion|age)\b"
    r"|\bhow old are you\b"
    r"|\bdo you (like|love|hate|believe|dream|sleep|eat)\b"
    r"|\bwhat do you think (about|of)\b"
    r"|\bwhat('s| is) the weather\b"
    r"|\bwhat('s| is) the (price|value|exchange rate) of (the )?(dollar|euro|bitcoin|gold|stock)\b"
    r"|\bwhat time is it\b"
    r"|\bwhat('s| is) (today|tomorrow)('s)? date\b"
    r"|\bwho (won|is winning)\b"
    r"|\bwhat('s| is) the news\b"
)

META_ANSWER_PROMPT = """\
You are the front door of IDI, a didactic natural-language database interface.
The user asked about the system or the connected database itself, not for actual
data rows. Answer in plain language using ONLY the facts given below -- never
invent tables, columns, or capabilities. Be warm and concise (3-5 sentences), and
close by suggesting one or two example questions the user could ask next about
this specific database.
"""

PERSONAL_OFFTOPIC_PROMPT = """\
You are IDI, a didactic natural-language database interface. The user just asked something
personal (directed at you) or unrelated to the connected database -- small talk, your
feelings/identity/opinions/beliefs, or a real-world fact like weather, prices, or news.
You have no live access to real-world data and no personal opinions or beliefs -- never
invent an answer to a factual real-world question (no fake weather, no fake prices, no
fake news, no fabricated personal stance). Respond warmly and briefly (1-2 sentences):
acknowledge the question lightly, state plainly that you're a database assistant without
real-world/live data or personal opinions, and invite the user back to a question about
the connected database.
"""

SQL_KNOWLEDGE_PROMPT = """\
You are IDI, a didactic natural-language database interface. The user asked about a
general SQL or relational-database concept (e.g. "what is a JOIN?", "explain a foreign
key"). Explain the concept briefly and clearly (2-4 sentences), then make it concrete by
illustrating it with the connected database's ACTUAL tables and columns, listed in the
facts below -- e.g. join two real tables on their real key column. Use ONLY tables and
columns that appear in the facts; never invent them. Close by inviting the user to try
one concrete example question against this database.
If the user is actually asking about THIS specific database itself (its name, what it
contains, its tables) rather than a general concept, answer that directly from the facts.
"""


class MetaQuestionFilter:
    """Detects and answers questions that don't require SQL generation at all."""

    def is_meta_question(self, query: str, profile: DBProfile) -> bool:
        q = query.lower().strip()
        if _SQL_SIGNAL_RE.search(q):
            return False
        if _META_RE.search(q) or _PERSONAL_OFFTOPIC_RE.search(q):
            return True
        if _SQL_KNOWLEDGE_RE.search(q):
            return True
        if not self._is_db_related(q, profile):
            return True  # off-topic: no DB relation, no SQL-knowledge signal
        return self._classify_with_llm(query)  # ambiguous but DB-vocab-adjacent

    def _is_db_related(self, q: str, profile: DBProfile) -> bool:
        return bool(_tokenize(q) & _domain_vocabulary(profile))

    def _classify_with_llm(self, query: str) -> bool:
        messages = [
            {
                "role": "system",
                "content": (
                    "Reply with ONLY the single word YES or NO, nothing else. "
                    "YES: the question asks what this system or database IS or can DO and "
                    "can be answered without querying any data rows, OR it is a personal "
                    "question directed at the assistant (feelings, identity, opinions, "
                    "beliefs), OR it asks about a real-world fact unrelated to the connected "
                    "database (weather, current prices, news, etc.) that no SQL query could "
                    "ever answer. "
                    "NO: answering it requires querying the connected database's actual data."
                ),
            },
            {"role": "user", "content": query},
        ]
        try:
            llm_service.unload_adapter()
            reply = llm_service.chat(messages, temperature=0.0).strip().upper()
            return reply.startswith("Y")
        except Exception as e:
            print(f"[MetaQuestionFilter] classification failed: {e} — defaulting to NO")
            return False

    def answer(self, query: str, profile: DBProfile) -> str:
        q = query.lower().strip()
        # Personal/off-topic takes priority: even if a question happens to also brush a
        # meta keyword, never let it be answered by grounding in DBProfile facts.
        if _PERSONAL_OFFTOPIC_RE.search(q) and not _META_RE.search(q):
            return self._answer_personal_offtopic(query)
        if _META_RE.search(q):
            return self._answer_about_system(query, profile)
        if _SQL_KNOWLEDGE_RE.search(q):
            return self._answer_sql_knowledge(query, profile)
        if not self._is_db_related(q, profile):
            return self._answer_personal_offtopic(query)
        # DB-vocab-adjacent and the LLM fallback classified it as meta -- ground it in
        # DBProfile facts rather than risk a generic redirect for a question that does
        # reference this database.
        return self._answer_about_system(query, profile)

    def _profile_facts(self, profile: DBProfile) -> str:
        """Canonical fact block for the connected database, shared by every grounded
        answer branch. Includes column names so a concept illustration (e.g. a JOIN)
        can reference real key columns."""
        table_lines = []
        for t in profile.tables:
            cols = ", ".join(c.name for c in t.columns)
            desc = t.description or "no description available"
            suffix = f" (columns: {cols})" if cols else ""
            table_lines.append(f"- {t.name}: {desc}{suffix}")
        tables = "\n".join(table_lines) or "(no tables introspected yet)"
        return (
            f"Database: {profile.db_name}\n"
            f"Domain description: {profile.domain_description or 'not provided'}\n"
            f"Tables:\n{tables}"
        )

    def _answer_about_system(self, query: str, profile: DBProfile) -> str:
        messages = [
            {"role": "system", "content": META_ANSWER_PROMPT},
            {
                "role": "user",
                "content": f"Database facts:\n{self._profile_facts(profile)}\n\n"
                f"User question: {query}",
            },
        ]
        llm_service.unload_adapter()
        return llm_service.chat(messages, temperature=0.3).strip()

    def _answer_personal_offtopic(self, query: str) -> str:
        messages = [
            {"role": "system", "content": PERSONAL_OFFTOPIC_PROMPT},
            {"role": "user", "content": query},
        ]
        llm_service.unload_adapter()
        return llm_service.chat(messages, temperature=0.4).strip()

    def _answer_sql_knowledge(self, query: str, profile: DBProfile) -> str:
        messages = [
            {"role": "system", "content": SQL_KNOWLEDGE_PROMPT},
            {
                "role": "user",
                "content": f"Database facts:\n{self._profile_facts(profile)}\n\n"
                f"User question: {query}",
            },
        ]
        llm_service.unload_adapter()
        return llm_service.chat(messages, temperature=0.3).strip()
