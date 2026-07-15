"""Orchestrator — real 7-agent pipeline with clarification branch + retry-on-verify-fail."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from backend.app.agents.clarification import Clarification, MetaQuestionFilter
from backend.app.agents.context_manager import ContextManager
from backend.app.agents.query_understanding import QueryUnderstanding
from backend.app.agents.sql_generator import SQLGenerator
from backend.app.agents.verification import VerificationAgent
from backend.app.models.envelope import (
    AgentEvent,
    AgentName,
    DBProfile,
    QueryResult,
    SqlCandidate,
)
from backend.app.services import adapter_registry
from backend.app.services.db.connector import get_connector
from backend.app.services.memory.sessions import (
    append_turn,
    create_session,
    get_recent_turns,
)


class Orchestrator:
    def __init__(self) -> None:
        self._active_db_name: str | None = None
        self._db = None
        self._db_profile: DBProfile | None = None
        self._context_mgr: ContextManager | None = None
        self._verification: VerificationAgent | None = None
        self._query_understanding = QueryUnderstanding()
        self._clarification = Clarification()
        self._meta_filter = MetaQuestionFilter()
        self._sql_generator = SQLGenerator()

    # -- database selection ----------------------------------------------------------

    def select_database(self, db_name: str) -> DBProfile:
        """(Re)build the connector/context/profile for db_name, unless it's
        already the active database. Only swaps instance state after a
        successful build, so a failed build never leaves partial state."""
        if db_name == self._active_db_name and self._db_profile is not None:
            return self._db_profile

        new_db = get_connector(db_name)
        new_db.connect()
        new_context_mgr = ContextManager(new_db)
        new_profile = new_context_mgr.build_profile()
        new_verification = VerificationAgent(new_db)

        self._db = new_db
        self._context_mgr = new_context_mgr
        self._verification = new_verification
        self._db_profile = new_profile
        self._active_db_name = db_name
        return new_profile

    # -- event helper --------------------------------------------------------------

    def _ev(
        self,
        sid: str,
        agent: AgentName,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentEvent:
        return AgentEvent(
            session_id=sid, agent=agent, status=status, message=message, payload=payload
        )

    # -- pipeline ------------------------------------------------------------------

    async def run(
        self, query: str, session_id: str | None = None
    ) -> AsyncGenerator[AgentEvent | QueryResult, None]:
        if self._db_profile is None or self._db is None:
            yield self._ev(
                session_id or "unknown",
                "context_manager",
                "error",
                "No database selected. Call POST /db/select first.",
            )
            yield QueryResult(session_id=session_id or "unknown", error="No database selected.")
            return

        sid = session_id or create_session(db_name=self._active_db_name)
        result = QueryResult(session_id=sid)
        append_turn(sid, "user", query)

        # -- 1. Context Manager ------------------------------------------------------
        yield self._ev(sid, "context_manager", "started", "Loading DB profile…")
        yield self._ev(
            sid,
            "context_manager",
            "done",
            f"Using cached profile for {self._active_db_name} "
            f"({len(self._db_profile.tables)} tables)",
            {"table_count": len(self._db_profile.tables)},
        )

        # -- 1.5 Meta-question filter (non-SQL questions about the DB/system) ------------
        if self._meta_filter.is_meta_question(query, self._db_profile):
            yield self._ev(
                sid, "clarification", "started", "Not a data question — answering directly…"
            )
            answer = self._meta_filter.answer(query, self._db_profile)
            yield self._ev(sid, "clarification", "done", "Answered", {"meta_answer": True})
            result.teaching_summary = answer
            append_turn(sid, "assistant", result.teaching_summary)
            yield result
            return

        # -- 2. Query Understanding --------------------------------------------------
        qu_label = adapter_registry.activate("query_understanding")
        yield self._ev(
            sid, "query_understanding", "started", "Parsing intent…", {"adapter": qu_label}
        )
        # Inject recent turns for multi-turn context
        recent = get_recent_turns(sid, n=4)
        contextualised_query = query
        if recent:
            history_str = "\n".join(f"{t['role']}: {t['content']}" for t in recent[:-1])
            contextualised_query = f"[History]\n{history_str}\n[Current] {query}"
        intent = self._query_understanding.parse(contextualised_query, self._db_profile)
        result.intent = intent
        yield self._ev(
            sid,
            "query_understanding",
            "done",
            intent.plain_restatement or "Intent parsed",
            intent.model_dump(),
        )

        # -- 3. Clarification (branch) -------------------------------------------------
        if self._clarification.needs_clarification(intent):
            clar_label = adapter_registry.activate("clarification")
            yield self._ev(
                sid,
                "clarification",
                "started",
                "Ambiguity detected — generating follow-up…",
                {"adapter": clar_label},
            )
            question = self._clarification.generate_question(intent)
            yield self._ev(
                sid, "clarification", "done", question, {"clarification_question": question}
            )
            result.teaching_summary = f"**Clarification needed:** {question}"
            yield result
            return  # Stop and wait for user reply

        # -- 4. SQL Generator ------------------------------------------------------------
        sql_label = adapter_registry.activate("sql_generator")
        yield self._ev(sid, "sql_generator", "started", "Generating SQL…", {"adapter": sql_label})
        try:
            candidate = self._sql_generator.generate(intent, self._db_profile)
            result.sql = candidate
            yield self._ev(
                sid,
                "sql_generator",
                "done",
                "SQL generated",
                {
                    "sql": candidate.sql[:300],
                    "rationale": candidate.rationale,
                    **(self._sql_generator.last_meta or {}),
                },
            )
        except Exception as e:
            yield self._ev(sid, "sql_generator", "error", str(e))
            result.error = str(e)
            yield result
            return

        # -- 5. Verification (with 1 repair loop) -------------------------------------------
        verify_label = adapter_registry.activate("verification")
        yield self._ev(
            sid,
            "verification",
            "started",
            "Verifying SQL (3-layer chain)…",
            {"adapter": verify_label},
        )
        verify = self._verification.verify(candidate, self._db_profile)

        if not verify.overall_passed and verify.repaired_sql:
            # One repair attempt
            yield self._ev(
                sid, "verification", "progress", f"Repair applied: {verify.repair_explanation}"
            )
            repaired_candidate = SqlCandidate(
                sql=verify.repaired_sql,
                rationale=candidate.rationale,
                generation_method=candidate.generation_method,
            )
            verify = self._verification.verify(repaired_candidate, self._db_profile)
            if verify.overall_passed:
                candidate = repaired_candidate
                result.sql = candidate

        if not verify.overall_passed:
            # One regeneration attempt: feed the failing layer's message (which now
            # carries the engine's real error, e.g. "no such column: t.artist_id")
            # back to the SQL Generator. A single bad generation must not be fatal
            # when the verifier can say exactly what was wrong with it.
            failure_msgs = "; ".join(
                layer.message
                for layer in (verify.syntax, verify.semantic, verify.sanity)
                if layer and not layer.passed and not layer.message.startswith("Skipped")
            )
            yield self._ev(
                sid,
                "verification",
                "progress",
                f"Verification failed ({failure_msgs}) — regenerating SQL once…",
            )
            adapter_registry.activate("sql_generator")
            try:
                feedback = f"Rejected SQL:\n{candidate.sql}\nReason: {failure_msgs}"
                regenerated = self._sql_generator.generate(
                    intent, self._db_profile, feedback=feedback
                )
                adapter_registry.activate("verification")
                reverify = self._verification.verify(regenerated, self._db_profile)
                if reverify.overall_passed:
                    candidate = regenerated
                    result.sql = candidate
                    verify = reverify
            except Exception as e:
                yield self._ev(sid, "verification", "progress", f"Regeneration failed: {e}")

        result.verify = verify
        if not verify.overall_passed:
            yield self._ev(
                sid,
                "verification",
                "error",
                "SQL failed all verification layers — not executed",
                verify.model_dump(),
            )
            result.error = "Verification failed."
            yield result
            return

        yield self._ev(sid, "verification", "done", "SQL passed all 3 layers", verify.model_dump())

        # -- 6. Execution --------------------------------------------------------------------
        yield self._ev(sid, "orchestrator", "progress", "Executing SQL…")
        try:
            rows = self._db.execute_read(candidate.sql)
            result.rows = rows
            result.row_count = len(rows)

            # Build teaching summary
            rationale = candidate.rationale or ""
            layers = (
                f"Syntax: {verify.syntax.message} | "
                f"Semantic: {verify.semantic.message} | "
                f"Sanity: {verify.sanity.message}"
            )
            result.teaching_summary = (
                f"**What I understood:** {intent.plain_restatement}\n\n"
                f"**Why this SQL:** {rationale}\n\n"
                f"**Verification:** {layers}\n\n"
                f"**Result:** {len(rows)} row(s) returned."
            )
            append_turn(
                sid, "assistant", result.teaching_summary, sql=candidate.sql, rows=rows[:10]
            )
            yield self._ev(
                sid, "orchestrator", "done", f"Done — {len(rows)} row(s)", {"row_count": len(rows)}
            )
        except Exception as e:
            yield self._ev(sid, "orchestrator", "error", str(e))
            result.error = str(e)

        yield result


orchestrator = Orchestrator()
