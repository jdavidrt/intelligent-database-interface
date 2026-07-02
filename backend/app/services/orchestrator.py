"""Orchestrator — real 7-agent pipeline with clarification branch + retry-on-verify-fail."""

from __future__ import annotations
from typing import AsyncGenerator, Any

from backend.app.models.envelope import (
    AgentEvent, AgentName, DBProfile, SqlCandidate, QueryResult,
)
from backend.app.services.llm_service import llm_service
from backend.app.services.db.connector import get_connector
from backend.app.agents.context_manager import ContextManager
from backend.app.agents.query_understanding import QueryUnderstanding
from backend.app.agents.clarification import Clarification
from backend.app.agents.sql_generator import SQLGenerator
from backend.app.agents.verification import VerificationAgent
from backend.app.services.memory.sessions import (
    create_session, append_turn, get_recent_turns,
)


class Orchestrator:
    def __init__(self) -> None:
        self._db = get_connector()
        self._db_profile: DBProfile | None = None
        self._context_mgr = ContextManager(self._db)
        self._query_understanding = QueryUnderstanding()
        self._clarification = Clarification()
        self._sql_generator = SQLGenerator()
        self._verification = VerificationAgent(self._db)

    # -- event helper --------------------------------------------------------------

    def _ev(
        self,
        sid: str,
        agent: AgentName,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentEvent:
        return AgentEvent(session_id=sid, agent=agent,
                          status=status, message=message, payload=payload)

    def _adapter_ev(self, sid: str, agent: AgentName) -> AgentEvent:
        """Emit the active-adapter note before an LLM agent turn (Gate D3 observes this)."""
        return self._ev(sid, agent, "progress", "Adapter active",
                        {"adapter": llm_service.active_adapter()})

    # -- pipeline ------------------------------------------------------------------

    async def run(
        self, query: str, session_id: str | None = None
    ) -> AsyncGenerator[AgentEvent | QueryResult, None]:
        sid = session_id or create_session(db_name="soundwave_db")
        result = QueryResult(session_id=sid)
        append_turn(sid, "user", query)

        # -- 1. Context Manager ------------------------------------------------------
        yield self._ev(sid, "context_manager", "started", "Loading DB profile…")
        try:
            self._db.connect()
            if self._db_profile is None:
                self._db_profile = self._context_mgr.build_profile()
            yield self._ev(sid, "context_manager", "done",
                           f"{len(self._db_profile.tables)} tables in DBProfile",
                           {"table_count": len(self._db_profile.tables)})
        except Exception as e:
            yield self._ev(sid, "context_manager", "error", str(e))
            result.error = str(e)
            yield result
            return

        # -- 2. Query Understanding --------------------------------------------------
        yield self._ev(sid, "query_understanding", "started", "Parsing intent…")
        # Inject recent turns for multi-turn context
        recent = get_recent_turns(sid, n=4)
        contextualised_query = query
        if recent:
            history_str = "\n".join(f"{t['role']}: {t['content']}" for t in recent[:-1])
            contextualised_query = f"[History]\n{history_str}\n[Current] {query}"
        intent = self._query_understanding.parse(contextualised_query, self._db_profile)
        yield self._adapter_ev(sid, "query_understanding")
        result.intent = intent
        yield self._ev(sid, "query_understanding", "done",
                       intent.plain_restatement or "Intent parsed",
                       intent.model_dump())

        # -- 3. Clarification (branch) -------------------------------------------------
        if self._clarification.needs_clarification(intent):
            yield self._ev(sid, "clarification", "started",
                           "Ambiguity detected — generating follow-up…")
            question = self._clarification.generate_question(intent)
            yield self._adapter_ev(sid, "clarification")
            yield self._ev(sid, "clarification", "done",
                           question, {"clarification_question": question})
            result.teaching_summary = f"**Clarification needed:** {question}"
            yield result
            return  # Stop and wait for user reply

        # -- 4. SQL Generator ------------------------------------------------------------
        yield self._ev(sid, "sql_generator", "started", "Generating SQL…")
        try:
            candidate = self._sql_generator.generate(intent, self._db_profile)
            yield self._adapter_ev(sid, "sql_generator")
            result.sql = candidate
            yield self._ev(sid, "sql_generator", "done",
                           "SQL generated",
                           {"sql": candidate.sql[:300], "rationale": candidate.rationale})
        except Exception as e:
            yield self._ev(sid, "sql_generator", "error", str(e))
            result.error = str(e)
            yield result
            return

        # -- 5. Verification (with 1 repair loop) -------------------------------------------
        yield self._ev(sid, "verification", "started", "Verifying SQL (3-layer chain)…")
        verify = self._verification.verify(candidate, self._db_profile)
        yield self._adapter_ev(sid, "verification")

        if not verify.overall_passed and verify.repaired_sql:
            # One repair attempt
            yield self._ev(sid, "verification", "progress",
                           f"Repair applied: {verify.repair_explanation}")
            repaired_candidate = SqlCandidate(
                sql=verify.repaired_sql,
                rationale=candidate.rationale,
                generation_method=candidate.generation_method,
            )
            verify = self._verification.verify(repaired_candidate, self._db_profile)
            if verify.overall_passed:
                candidate = repaired_candidate
                result.sql = candidate

        result.verify = verify
        if not verify.overall_passed:
            yield self._ev(sid, "verification", "error",
                           "SQL failed all verification layers — not executed",
                           verify.model_dump())
            result.error = "Verification failed."
            yield result
            return

        yield self._ev(sid, "verification", "done",
                       "SQL passed all 3 layers",
                       verify.model_dump())

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
            append_turn(sid, "assistant", result.teaching_summary,
                        sql=candidate.sql, rows=rows[:10])
            yield self._ev(sid, "orchestrator", "done",
                           f"Done — {len(rows)} row(s)",
                           {"row_count": len(rows)})
        except Exception as e:
            yield self._ev(sid, "orchestrator", "error", str(e))
            result.error = str(e)

        yield result


orchestrator = Orchestrator()
