from __future__ import annotations

import json
import logging
import re
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
from auth_service.orchestration.candidate_eval import evaluate_candidates_batch
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
from auth_service.tools.registry import build_turn_registry

logger = logging.getLogger(__name__)

MAX_LLM_CALLS_PER_TURN = 2

_WEB_SEARCH_HINT = re.compile(
    r"\b(deadline|scholarship|university|admission|visa|ielts|toefl|gre|ranking|"
    r"tuition|application fee|current|latest|202[4-9]|2030)\b",
    re.IGNORECASE,
)


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
        # Optional Postgres checkpointing adds remote round-trips on every node;
        # disable via ENABLE_GRAPH_CHECKPOINT=false for lower chat latency.
        if settings.enable_graph_checkpoint:
            self._graph = build_pai_graph(self).compile(checkpointer=self._checkpointer)
        else:
            self._graph = build_pai_graph(self).compile()
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
        # Context is loaded once inside the graph (node_load_student_context).
        # Prefetch semantic memory here only — conversation agent must not re-recall via tools.
        semantic_ctx = await self._memory.recall(user_message.content)
        state: PAIState = {
            "person_id": str(person.id),
            "conversation_id": str(conversation_id),
            "user_message_id": str(user_message.id),
            "user_message": user_message.content,
            "student_context": None,
            "student_context_json": "{}",
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
        if self._memory:
            self._memory.hydrate_conversation(pack.recent_messages)
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
        state["candidate_results"] = await evaluate_candidates_batch(
            self._session, self._person, list(state.get("fact_candidates") or [])
        )
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
            # Deterministic semantic memory from accepted facts (not LLM tool choice).
            if self._memory and applied:
                for change in applied:
                    if change.status in ("rejected",):
                        continue
                    try:
                        await self._memory.remember(
                            f"Vault {change.status}: {change.field_key} "
                            f"(confidence={change.confidence})",
                            metadata={
                                "type": "vault_fact",
                                "source": "deterministic_apply",
                                "field_key": change.field_key,
                                "conversation_id": state["conversation_id"],
                            },
                        )
                    except Exception:
                        logger.exception("Deterministic memory write failed")
        state["applied_vault_changes"] = applied
        state["pending_confirmations"] = pending
        if self._run:
            self._run.current_step = "refresh_student_context"
        return state

    async def node_refresh_student_context(self, state: PAIState) -> PAIState:
        assert self._session and self._person
        applied = state.get("applied_vault_changes") or []
        if not applied:
            # No vault mutations — keep context from load_student_context.
            return state
        applied_json = [c.model_dump() for c in applied]
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
        semantic_ctx = state.get("semantic_memory_context") or ""
        allow_web = bool(
            self._settings.enable_counselor_tools
            and self._settings.tavily_api_key
            and _WEB_SEARCH_HINT.search(state["user_message"] or "")
        )
        registry = build_turn_registry(
            enable_web_search=allow_web,
            enable_semantic_recall=False,  # already prefetched into semantic_ctx
            enable_remember=False,  # avoid extra tool round-trips on normal turns
        )
        result = await self._conversation_agent.respond(
            current_message=state["user_message"],
            student_context_json=state.get("student_context_json") or "{}",
            recent_messages_json="[]",
            known_facts_json="{}",
            missing_critical_fields_json="[]",
            pending_confirmations_json=json.dumps(
                [p.model_dump() for p in state.get("pending_confirmations") or []]
            ),
            active_tasks_json="[]",
            applied_vault_changes_json=json.dumps(
                [c.model_dump() for c in state.get("applied_vault_changes") or []]
            ),
            task_results_json=json.dumps([]),
            semantic_memory_context=semantic_ctx,
            memory=self._memory,
            person_id=state["person_id"],
            conversation_id=state["conversation_id"],
            tool_registry=registry,
            enable_tools=allow_web,
        )
        state["assistant_result"] = result
        state["assistant_reply"] = result.reply
        state["task_proposals"] = result.task_proposals
        state["tool_trace"] = list(self._conversation_agent.last_tool_trace or [])
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
