from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.config import Settings
from auth_service.conversations.models import Message, OrchestrationRun
from auth_service.conversations import service as conv_svc
from auth_service.data.db import get_session_factory
from auth_service.ingestion.vault_apply import process_candidates
from auth_service.llm.gateway import LLMGateway
from auth_service.memory.service import PersonMemoryService
from auth_service.orchestration.agents import FactExtractionAgent, StudentConversationAgent
from auth_service.orchestration.candidate_eval import evaluate_candidate_with_context
from auth_service.orchestration.checkpoint import get_graph_checkpointer
from auth_service.orchestration.context import (
    build_student_context_pack,
    context_pack_to_json,
)
from auth_service.orchestration.graph import build_pai_graph
from auth_service.orchestration.routing import should_extract_facts
from auth_service.orchestration.schemas import (
    PendingConfirmation,
    RunError,
    VaultChange,
)
from auth_service.orchestration.state import PAIState
from auth_service.person.models import Person
from auth_service.tasks.service import process_task_proposals

logger = logging.getLogger(__name__)

MAX_LLM_CALLS_PER_TURN = 2


class PAIOrchestrator:
    """Central control plane for student counseling turns."""

    def __init__(
        self,
        settings: Settings,
        gateway: LLMGateway | None = None,
        *,
        checkpointer=None,
        fact_agent: FactExtractionAgent | None = None,
        conversation_agent: StudentConversationAgent | None = None,
    ) -> None:
        self._settings = settings
        self._gateway = gateway or LLMGateway(settings)
        self._fact_agent = fact_agent or FactExtractionAgent(self._gateway)
        self._conversation_agent = conversation_agent or StudentConversationAgent(
            self._gateway, settings=settings
        )
        self._checkpointer = checkpointer if checkpointer is not None else get_graph_checkpointer()
        self._graph = build_pai_graph(self).compile(checkpointer=self._checkpointer)
        self._session: AsyncSession | None = None
        self._person: Person | None = None
        self._run: OrchestrationRun | None = None
        self._memory: PersonMemoryService | None = None

    async def run_chat_turn(
        self,
        session: AsyncSession,
        person: Person,
        conversation_id: uuid.UUID,
        user_message: Message,
        *,
        run: OrchestrationRun,
    ) -> PAIState:
        self._session = session
        self._person = person
        self._run = run
        self._memory = PersonMemoryService(
            self._settings,
            person.id,
            session_factory=get_session_factory(self._settings),
        )
        pack = await build_student_context_pack(
            session, person, conversation_id=conversation_id, settings=self._settings
        )
        self._memory.hydrate_conversation(pack.recent_messages)
        semantic_ctx = await self._memory.recall(user_message.content)
        state: PAIState = {
            "person_id": str(person.id),
            "conversation_id": str(conversation_id),
            "user_message_id": str(user_message.id),
            "user_message": user_message.content,
            "student_context": pack,
            "student_context_json": context_pack_to_json(pack),
            "extraction_required": should_extract_facts(user_message.content),
            "fact_candidates": [],
            "candidate_results": [],
            "applied_vault_changes": [],
            "pending_confirmations": [],
            "task_proposals": [],
            "task_results": [],
            "assistant_result": None,
            "assistant_reply": "",
            "assistant_message_id": None,
            "run_id": str(run.id),
            "run_status": "running",
            "errors": [],
            "orchestration_llm_calls": 0,
            "semantic_memory_context": semantic_ctx,
            "tool_trace": [],
        }
        run.current_step = "save_user_message"
        run.provider = self._settings.llm_default_provider
        graph_config = {"configurable": {"thread_id": str(run.id)}}
        try:
            final = await self._graph.ainvoke(state, config=graph_config)
            run.status = final.get("run_status", "completed")
            run.current_step = "completed"
            run.completed_at = datetime.now(UTC)
            return final
        except Exception as exc:
            logger.exception("Orchestration failed")
            run.status = "failed"
            run.error_code = "ORCHESTRATION_ERROR"
            run.completed_at = datetime.now(UTC)
            raise exc
        finally:
            self._session = None
            self._person = None
            self._run = None
            self._memory = None

    async def node_save_user_message(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        await conv_svc.get_conversation_owned(
            self._session,
            uuid.UUID(state["person_id"]),
            uuid.UUID(state["conversation_id"]),
        )
        if self._run:
            self._run.current_step = "load_student_context"
        return state

    async def node_load_student_context(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        pack = await build_student_context_pack(
            self._session,
            self._person,
            conversation_id=uuid.UUID(state["conversation_id"]),
            settings=self._settings,
        )
        state["student_context"] = pack
        state["student_context_json"] = context_pack_to_json(pack)
        if self._run:
            self._run.current_step = "route_turn"
        return state

    async def node_route_turn(self, state: PAIState) -> PAIState:
        state["extraction_required"] = should_extract_facts(state["user_message"])
        return state

    async def node_extract_facts(self, state: PAIState) -> PAIState:
        if (state.get("orchestration_llm_calls") or 0) >= MAX_LLM_CALLS_PER_TURN:
            state.setdefault("errors", []).append(
                RunError(code="LLM_LIMIT", message="LLM call limit reached", step="extract_facts")
            )
            return state
        candidates = await self._fact_agent.extract_from_chat(
            user_message=state["user_message"],
            user_message_id=state["user_message_id"],
        )
        state["fact_candidates"] = candidates
        state["orchestration_llm_calls"] = (state.get("orchestration_llm_calls") or 0) + 1
        if self._run:
            self._run.current_step = "validate_candidates"
        return state

    async def node_validate_candidates(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        results = []
        for c in state.get("fact_candidates") or []:
            results.append(
                await evaluate_candidate_with_context(self._session, self._person, c)
            )
        state["candidate_results"] = results
        if self._run:
            self._run.current_step = "apply_vault_changes"
        return state

    async def node_apply_vault_changes(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        to_apply = []
        pending: list[PendingConfirmation] = []
        for r in state.get("candidate_results") or []:
            if r.outcome in ("accept", "reinforce", "pending_confirmation"):
                to_apply.append(r.candidate)
            if r.outcome == "pending_confirmation":
                pending.append(
                    PendingConfirmation(
                        field_key=r.candidate.field_key,
                        value=r.candidate.value,
                        evidence_text=r.candidate.evidence_text,
                        source_reference=r.candidate.source_reference,
                    )
                )
            if r.outcome == "conflict":
                pending.append(
                    PendingConfirmation(
                        field_key=r.candidate.field_key,
                        value=r.candidate.value,
                        evidence_text=r.candidate.evidence_text,
                        source_reference=r.candidate.source_reference,
                    )
                )
        applied: list[VaultChange] = []
        if to_apply:
            outcomes, pend_llm = await process_candidates(
                self._session, self._person, to_apply
            )
            for o in outcomes:
                applied.append(
                    VaultChange(
                        field_key=o.field_key, status=o.status, confidence=o.confidence
                    )
                )
            for p in pend_llm:
                pending.append(
                    PendingConfirmation(
                        field_key=p.field_key,
                        value=p.value,
                        evidence_text=p.evidence_text,
                        source_reference=p.source_reference,
                    )
                )
            await self._session.commit()
        state["applied_vault_changes"] = applied
        state["pending_confirmations"] = pending
        if self._run:
            self._run.current_step = "refresh_student_context"
        return state

    async def node_refresh_student_context(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        applied_json = [c.model_dump() for c in state.get("applied_vault_changes") or []]
        pack = await build_student_context_pack(
            self._session,
            self._person,
            conversation_id=uuid.UUID(state["conversation_id"]),
            settings=self._settings,
            applied_vault_changes_turn=applied_json,
        )
        state["student_context"] = pack
        state["student_context_json"] = context_pack_to_json(pack)
        return state

    async def node_run_conversation_agent(self, state: PAIState) -> PAIState:
        if (state.get("orchestration_llm_calls") or 0) >= MAX_LLM_CALLS_PER_TURN:
            state["assistant_reply"] = (
                "I'm having trouble processing that right now. Please try again shortly."
            )
            state["run_status"] = "degraded"
            return state
        pack = state.get("student_context")
        known_facts = {}
        if pack:
            known_facts = {
                "vault_fields": pack.applicable_vault_fields,
                "typed_profile": pack.typed_profile_summary,
            }
        semantic_ctx = state.get("semantic_memory_context") or ""
        if self._memory and not semantic_ctx:
            semantic_ctx = await self._memory.recall(state["user_message"])
            state["semantic_memory_context"] = semantic_ctx
        result = await self._conversation_agent.respond(
            current_message=state["user_message"],
            student_context_json=state.get("student_context_json") or "{}",
            recent_messages_json=json.dumps(pack.recent_messages if pack else []),
            known_facts_json=json.dumps(known_facts),
            missing_critical_fields_json=json.dumps(
                pack.missing_critical_fields if pack else []
            ),
            pending_confirmations_json=json.dumps(
                [p.model_dump() for p in state.get("pending_confirmations") or []]
            ),
            active_tasks_json=json.dumps(pack.active_tasks if pack else []),
            applied_vault_changes_json=json.dumps(
                [c.model_dump() for c in state.get("applied_vault_changes") or []]
            ),
            task_results_json=json.dumps([]),
            semantic_memory_context=semantic_ctx,
            memory=self._memory,
            person_id=state["person_id"],
            conversation_id=state["conversation_id"],
        )
        state["assistant_result"] = result
        state["assistant_reply"] = result.reply
        state["task_proposals"] = result.task_proposals
        state["orchestration_llm_calls"] = (state.get("orchestration_llm_calls") or 0) + 1
        if self._memory:
            self._memory.record_turn(user=state["user_message"], assistant=result.reply)
        if self._run:
            self._run.current_step = "process_tasks"
        return state

    async def node_process_tasks(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        proposals = state.get("task_proposals") or []
        if proposals:
            results = await process_task_proposals(
                self._session,
                self._person,
                proposals,
                conversation_id=uuid.UUID(state["conversation_id"]),
            )
            await self._session.commit()
            state["task_results"] = results
        if self._run:
            self._run.current_step = "save_assistant_message"
        return state

    async def node_save_assistant_message(self, state: PAIState) -> PAIState:
        state["run_status"] = state.get("run_status") or "completed"
        if self._run:
            self._run.decision_rationale = (
                state.get("assistant_result").suggested_next_step
                if state.get("assistant_result")
                else None
            )
        return state
