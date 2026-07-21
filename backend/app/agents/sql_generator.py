"""SQL Generator — NL->SQL with rationale, grounded in DBProfile + ChromaDB context."""

from __future__ import annotations

import json
import re

from backend.app.agents.sql_emitter import build_query_schema, render_sql
from backend.app.config import settings
from backend.app.models.envelope import DBProfile, Intent, SqlCandidate
from backend.app.services import clock, temporal
from backend.app.services.db.join_graph import JoinGraph
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


PLAN_SYSTEM_PROMPT = """\
You are the query-planning step of IDI's SQL Generator. Given a user intent and
the database schema, select the MINIMAL set of tables needed to answer the
question, plus the output columns the answer must show. Do not add tables the
question does not need — every extra table multiplies rows. Respond with JSON
only.
"""


EMIT_SYSTEM_PROMPT = """\
You are the SQL emission step of IDI's SQL Generator. Fill in the query object
for the question below. Every table, column and join key you can choose is
already restricted to the locked query plan — you cannot name anything that does
not exist, so choose from what you are offered rather than writing SQL.

Rules:
1. `select` is the answer's shape. If the question asks "how many", "total",
   "average", "highest" — set `function` (COUNT / SUM / AVG / MIN / MAX /
   COUNT_DISTINCT). Returning raw rows where an aggregate was asked for is wrong.
2. Filter on codes, not on labels. If the schema says a column stores an integer
   code, `value` must be that code.
3. `joins` only for tables in the plan. A question about one table needs none.
4. `order_by.select_index` is 1-based into your own `select` list — that is how
   you order by a computed count.
5. Do NOT write a date filter: a relative time window is applied for you. Just
   set `time_column` to the date column the window applies to.
6. Set `expressible` to false — and nothing else — if the question genuinely
   needs a CTE, a subquery, a window function, UNION, CASE, or a self-join.
   Answering those with this object would silently give a wrong answer; saying
   so hands the question to a more capable path.

Respond with the JSON object only.
"""


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z_]+", text.lower()))


_QUALIFIED_EQ_RE = re.compile(r"\b([A-Za-z_]\w*)\.\w+\s*=\s*([A-Za-z_]\w*)\.\w+")


def _tables_in_feedback(feedback: str, profile: DBProfile) -> set[str]:
    """Real table names inside the qualified join equalities of a verifier
    rejection. The semantic layer spells out the legal chain as
    `table.col = table.col` pairs — those tables are exactly the ones the
    corrected query must join through. Aliases from the rejected SQL (`da`,
    `pe`) match no real table and drop out."""
    known = {t.name.lower() for t in profile.tables}
    return {
        name.lower()
        for m in _QUALIFIED_EQ_RE.finditer(feedback)
        for name in m.groups()
        if name.lower() in known
    }


def _linked_tables(intent: Intent, profile: DBProfile) -> set[str]:
    """Deterministic schema linking: tables whose name (or singular form)
    literally appears in the question or the extracted entities. Conservative
    on purpose — a missed match only means no precomputed plan gets injected,
    while a wrong match would inject a misleading one."""
    tokens = _tokenize(
        " ".join([intent.raw_query or ""] + intent.entities + intent.requested_fields)
    )
    matched: set[str] = set()
    for t in profile.tables:
        name = t.name.lower()
        singular = name[:-1] if name.endswith("s") else name
        if name in tokens or singular in tokens:
            matched.add(name)
    return matched


def _render_join_edges(edges: list[str], profile: DBProfile, indent: str) -> str:
    """Plan edges, one per line, with transitive shortcuts flagged.

    An edge join_tree() derives (both columns FK-chain to the same key) is not
    on the prompt's foreign-key line, so without this annotation the model is
    told to copy verbatim an equality the same prompt calls nonexistent."""
    fk_labels = {f"{src} = {tgt}".lower() for src, tgt in profile.relationship_edges}
    rendered = []
    for edge in edges:
        note = "" if edge.lower() in fk_labels else "   (shortcut through a shared key — valid)"
        rendered.append(f"{indent}{edge}{note}")
    return "\n".join(rendered)


def _render_coded_values(col: str, mapping: dict[str, str]) -> str:
    """Coded values as an instruction, not as a lookup table to invert.

    The old rendering was `Coded values for users.status: 0->inactive,
    1->active, 2->banned`, which states the mapping in the direction opposite to
    the one a filter needs: to answer "how many banned users" the model has to
    read it backwards. In the 2026-07-21 pilot it did not, and emitted
    `WHERE status = 'banned'` against an integer column — syntactically valid,
    silently zero rows, so verification had nothing to reject either.

    Codes that equal their meaning (`event_type: play->play`) carry no mapping
    at all; for those the useful fact is the closed set of allowed literals.
    """
    literal = all(str(code) == str(meaning) for code, meaning in mapping.items())
    if literal:
        allowed = ", ".join(f"'{code}'" for code in mapping)
        return f"{col} accepts exactly these values: {allowed}. Any other literal matches nothing."
    numeric = all(str(code).lstrip("-").isdigit() for code in mapping)
    kind = "INTEGER" if numeric else "CODE"
    pairs = ", ".join(f"'{meaning}' is {col} = {code}" for code, meaning in mapping.items())
    return (
        f"{col} stores an {kind} code, never the word: {pairs}. "
        f"Filter on the code ({col} = {next(iter(mapping))}), never on the label."
    )


def _build_schema_summary(profile: DBProfile, focus: set[str] | None = None) -> str:
    """Schema for the prompt. `focus` narrows the *detail*, never the table list.

    When a locked plan exists, only its tables get their columns spelled out.
    The pilot showed why: the emitter was handed a plan naming
    `subscription_plans` alone and still wrote `JOIN subscriptions ON ... WHERE
    s.has_downloads`, a column it could only have found in the full 19-table
    dump printed above the plan. Telling a 3B model "use ONLY these tables"
    directly underneath every column of every other table is a contradiction,
    and it resolved it the wrong way.

    The complete table *list* stays complete regardless — it is the
    hallucinated-table guard, and truncating it would invite the opposite error.
    """
    lines = [f"Database: {profile.db_name}"]
    if profile.domain_description:
        lines.append(f"Domain: {profile.domain_description}")
    # Closed table list: small models respect a short explicit enumeration far
    # better than one implied by the per-table detail below (hallucinated-table guard).
    lines.append(
        "Tables (complete list — a name not listed here is NOT a table): "
        + ", ".join(t.name for t in profile.tables)
    )
    detailed = [t for t in profile.tables if focus is None or t.name.lower() in focus]
    if focus is not None:
        lines.append(
            "Columns are listed below for the tables your query plan selected. "
            "The other tables exist but are not part of this question."
        )
    for t in detailed:
        cols = ", ".join(
            f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''}"
            + (", PK" if c.is_primary_key else "")
            + (f", FK->{c.references}" if c.is_foreign_key and c.references else "")
            + ")"
            for c in t.columns
        )
        lines.append(f"  {t.name}: {cols}")
    # Closed join map: every real FK relationship, spelled out. Small models
    # hallucinate join keys (e.g. artists.user_id) when left to guess them.
    #
    # The exclusivity claim is deliberately worded to admit the query plan's
    # shortcuts. join_tree() legitimately emits transitive equalities that are
    # NOT raw FKs (e.g. `play_events.track_id = track_artists.track_id`, where
    # both columns FK-chain to tracks.track_id) — of 86 legal equalities in
    # soundwave only 29 are raw FKs. Claiming this list is exhaustive while the
    # plan below says "copy these verbatim" put two contradictory instructions
    # in one prompt, on the most common query shape in the project.
    if profile.relationship_edges:
        lines.append(
            "Foreign keys (the schema's real relationships): "
            + "; ".join(f"{src} = {tgt}" for src, tgt in profile.relationship_edges)
            + ". Every JOIN's ON clause MUST be one of these equalities, or one of the "
            "equivalences given in the query plan below — those are shortcuts through a "
            "shared key and are equally valid. Any other join key does NOT exist."
        )

    # Glossary and coded values are filtered to the focus tables too, but only
    # for entries that name a table. Bare keys (`is_exp`, `trk_dur_ms`) apply to
    # whichever table owns them and are always kept — dropping those would lose
    # exactly the abbreviation hints the model needs most.
    def _in_focus(key: str) -> bool:
        if focus is None or "." not in key:
            return True
        return key.split(".", 1)[0].lower() in focus

    glossary = {k: v for k, v in profile.glossary.items() if _in_focus(k)}
    if glossary:
        lines.append("Glossary: " + ", ".join(f"{k}={v}" for k, v in glossary.items()))
    for col, mapping in profile.coded_value_maps.items():
        if mapping and _in_focus(col):
            lines.append(_render_coded_values(col, mapping))
    if profile.source_of_truth:
        lines.append(
            "Source-of-truth notes (ambiguous concept -> canonical source): "
            + "; ".join(f"{k} -> {v}" for k, v in profile.source_of_truth.items())
        )
    return "\n".join(lines)


class SQLGenerator:
    def __init__(self) -> None:
        self.last_meta: dict | None = None

    # -- Schema-grounded planning ---------------------------------------------------

    def _constrained_plan(
        self, intent: Intent, profile: DBProfile, feedback: str | None = None
    ) -> dict | None:
        """Constrained-decoding plan step ("tokenized vocabulary").

        llama.cpp compiles the JSON Schema below — whose enums are exactly the
        schema's table names, FK join edges and qualified columns — into a GBNF
        grammar, so the sampler CANNOT emit an identifier outside the schema:
        hallucination is blocked at token level, not just caught afterwards.

        The model only *chooses tables and output columns*; the join edges are
        then recomputed deterministically from the FK graph (join_tree), so the
        final plan's ON clauses are correct by construction, multi-hop
        intermediates included. Any failure (older llama.cpp, timeout, bad
        JSON) degrades gracefully to None — generation proceeds unplanned and
        the verification chain remains the safety net.
        """
        if not settings.constrained_planning or not profile.tables:
            return None
        table_names = [t.name for t in profile.tables]
        edge_labels = [f"{s} = {t}" for s, t in profile.relationship_edges]
        column_names = [f"{t.name}.{c.name}" for t in profile.tables for c in t.columns]
        schema = {
            "type": "object",
            "properties": {
                "tables": {
                    "type": "array",
                    "items": {"type": "string", "enum": table_names},
                    "minItems": 1,
                    "maxItems": 6,
                },
                "join_on": {
                    "type": "array",
                    "items": {"type": "string", "enum": edge_labels},
                    "maxItems": 8,
                },
                "output_columns": {
                    "type": "array",
                    "items": {"type": "string", "enum": column_names},
                    "minItems": 1,
                    "maxItems": 10,
                },
            },
            "required": ["tables", "join_on", "output_columns"],
        }
        user_content = (
            f"Schema:\n{_build_schema_summary(profile)}\n\n"
            f"User intent: {intent.plain_restatement or intent.raw_query}\n"
            f"Original question: {intent.raw_query}\n"
            "Pick the minimal tables, the join edges connecting them, and "
            "the output columns."
        )
        if feedback:
            user_content += (
                "\n\nA previous plan produced SQL the verification layer rejected:\n"
                f"{feedback}\n"
                "Re-plan avoiding the rejected pattern; when the rejection names a "
                "legal join chain, include every table on that chain."
            )
        messages = [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        try:
            raw = llm_service.chat(
                messages,
                temperature=0.1,
                timeout=60,
                extra={"response_format": {"type": "json_object", "schema": schema}},
            )
            match = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(match.group()) if match else None
        except Exception as e:
            print(f"[SQLGenerator] constrained plan unavailable ({e}) — generating without")
            return None
        if not isinstance(data, dict):
            return None
        tables = {t for t in data.get("tables", []) if isinstance(t, str) and t}
        if not tables:
            return None
        # Reconcile: every output column's owner table must be in the plan —
        # otherwise the prompt says "use ONLY these tables" while offering a
        # column from a table outside them, and the model resolves the
        # contradiction by hallucinating an alias for the missing table (the
        # phantom `a.name` in the "most reproduced artists" failure).
        known = {t.name.lower() for t in profile.tables}
        for qualified in data.get("output_columns", []):
            if isinstance(qualified, str):
                owner = qualified.split(".", 1)[0].strip().lower()
                if owner in known:
                    tables.add(owner)
        # On regeneration, the verifier's legal-chain hint names the tables the
        # corrected query must route through — fold them in deterministically.
        if feedback:
            tables |= _tables_in_feedback(feedback, profile)
        data["tables"] = sorted(tables)
        # Deterministic completion: replace the model's edge picks with the
        # minimal FK join tree over the reconciled tables (intermediates included).
        tree = JoinGraph(profile.relationship_edges).join_tree(tables)
        if tree is not None:
            edges, all_tables = tree
            data["tables"] = sorted(all_tables)
            data["join_on"] = edges
        return data

    # -- Structured emission ------------------------------------------------------------

    def _structured_emission(
        self,
        intent_lines: list[str],
        profile: DBProfile,
        plan: dict | None,
        time_predicate: str | None,
    ) -> tuple[str, str] | None:
        """Emit SQL through a grammar-constrained query object (Step 2).

        Returns (sql, rationale), or None to hand back to free-form generation.
        Every `return None` here is a deliberate decline: this path is only
        allowed to *win* on the shapes it fully represents.
        """
        if not settings.structured_sql or not plan:
            return None
        schema = build_query_schema(profile, plan)
        if schema is None:
            return None
        try:
            raw = llm_service.chat(
                [
                    {"role": "system", "content": EMIT_SYSTEM_PROMPT},
                    {"role": "user", "content": "\n\n".join(intent_lines)},
                ],
                temperature=0.1,
                extra={"response_format": {"type": "json_object", "schema": schema}},
            )
            match = re.search(r"\{[\s\S]*\}", raw)
            query = json.loads(match.group()) if match else None
        except Exception as e:  # noqa: BLE001 — any failure means "use free-form"
            print(f"[SQLGenerator] structured emission unavailable ({e}) — free-form")
            return None
        if not isinstance(query, dict):
            return None
        sql = render_sql(query, profile, time_predicate=time_predicate)
        if sql is None:
            print("[SQLGenerator] structured emission declined the shape — free-form")
            return None
        self.last_meta = {**(self.last_meta or {}), "emission": "structured"}
        tables = ", ".join(plan.get("tables", []))
        return sql, (
            f"Built from the locked query plan over {tables}: the table set, join keys and "
            "column names were chosen from the schema's closed vocabulary, so every "
            "identifier in this query is guaranteed to exist."
        )

    # -- Generation --------------------------------------------------------------------

    def generate(
        self, intent: Intent, profile: DBProfile, feedback: str | None = None
    ) -> SqlCandidate:
        context_passages = query_context(intent.raw_query, n_results=4)
        context_str = "\n".join(context_passages)

        # Plan every attempt. Reusing attempt 1's plan on regeneration would
        # re-lock the very table selection the verifier just rejected (and
        # contradict its fix) — instead the rejection feedback goes to the
        # planner too, and its legal-chain tables are folded in.
        #
        # The plan is computed before the schema summary because it now decides
        # how much of the schema the summary spells out. The planner itself
        # still sees every table (it has to choose from all of them); only the
        # emitter's view is narrowed.
        plan = self._constrained_plan(intent, profile, feedback=feedback)
        focus = {t.lower() for t in plan["tables"]} if plan else None
        schema_summary = _build_schema_summary(profile, focus=focus)

        # A relative window is computed once and reused: the free-form prompt
        # states it as a STRICT instruction, and structured emission applies it
        # deterministically to the chosen date column.
        time_predicate: str | None = None
        window = (
            temporal.extract_relative_window(f"{intent.time_range} {intent.raw_query}")
            if intent.time_range
            else None
        )
        if window:
            time_predicate = temporal.required_predicate(*window)

        intent_lines = [
            f"Schema:\n{schema_summary}",
            f"Relevant context:\n{context_str}",
            clock.date_context(),
            f"User intent: {intent.plain_restatement}",
            f"Original query: {intent.raw_query}",
        ]

        # Schema-grounded query plan. Preferred source: the constrained-decoding
        # plan (identifiers guaranteed valid at sampling level). Fallback: pure
        # deterministic linking — tables literally named in the question,
        # connected through the FK graph. Either way the model receives the
        # exact multi-hop ON clauses instead of having to derive them (the
        # EC-08 failure mode: inventing `play_events.artist_id`).
        if plan:
            plan_lines = [f"  Tables (use ONLY these): {', '.join(plan['tables'])}"]
            if plan.get("join_on"):
                plan_lines.append(
                    "  JOIN ON clauses (copy verbatim, one per JOIN — this is the "
                    "complete legal set for these tables):\n"
                    + _render_join_edges(plan["join_on"], profile, "    ")
                )
            if plan.get("output_columns"):
                plan_lines.append(
                    f"  Candidate output columns: {', '.join(plan['output_columns'])}"
                )
            intent_lines.append(
                "Query plan (LOCKED — selected from the schema's closed vocabulary; "
                "every identifier below is guaranteed valid):\n" + "\n".join(plan_lines)
            )
        else:
            linked = _linked_tables(intent, profile)
            if feedback:
                linked |= _tables_in_feedback(feedback, profile)
            if len(linked) >= 2:
                tree = JoinGraph(profile.relationship_edges).join_tree(linked)
                if tree is not None and tree[0]:
                    edges, all_tables = tree
                    intent_lines.append(
                        f"Precomputed join plan for {', '.join(sorted(all_tables))} "
                        "(derived from the FK graph — if you join these tables, copy "
                        "these ON clauses verbatim, intermediates included):\n"
                        + _render_join_edges(edges, profile, "  ")
                    )
        if intent.time_range:
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
        # Query Understanding has always parsed these and they never reached the
        # prompt. "How long is the average track in minutes?" was answered with
        # `SELECT trk_dur_ms / 60000.0 FROM tracks` — 48 per-row values instead
        # of one average, with the parsed AVG sitting unused in the envelope.
        if intent.metrics:
            intent_lines.append(
                "Aggregations the answer requires (apply these in the SELECT list — "
                "the answer is the aggregate, not the raw rows): " + ", ".join(intent.metrics)
            )
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

        # Structured emission first (SQL_HARDENING_PLAN Step 2): the model fills
        # a query object whose identifier slots are enums from the plan, and the
        # SQL is rendered deterministically. Declines — an inexpressible shape,
        # an unrenderable object — fall through to free-form generation below,
        # so this can only add correctness, never remove reach.
        structured = self._structured_emission(intent_lines, profile, plan, time_predicate)
        if structured is not None:
            sql, rationale = structured
            return SqlCandidate(
                sql=sql,
                rationale=rationale,
                generation_method=(
                    "lora" if llm_service.active_adapter() == "sql_generator" else "base_model"
                ),
                tables_used=list(plan.get("tables", [])) if plan else [],
                columns_used=list(plan.get("output_columns", [])) if plan else [],
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(intent_lines)},
        ]

        raw, self.last_meta = llm_service.chat_with_meta(messages, temperature=0.2)
        self.last_meta = {**(self.last_meta or {}), "emission": "free_form"}

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
            tables_used=list(plan.get("tables", [])) if plan else [],
            columns_used=list(plan.get("output_columns", [])) if plan else [],
        )
