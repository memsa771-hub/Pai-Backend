from __future__ import annotations

import logging
from typing import Any

from auth_service.config import Settings, get_settings
from auth_service.llm.gateway import LLMGateway
from auth_service.llm.schemas import LLMMessage
from auth_service.memory.service import PersonMemoryService
from auth_service.orchestration.counselor_graph import run_counselor_with_tools
from auth_service.orchestration.prompts import render_template
from auth_service.orchestration.schemas import (
    ConversationResult,
    FactExtractionResult,
    VaultCandidate,
)
from auth_service.tools.registry import ToolRegistry, build_default_registry
from auth_service.vault.catalog import extraction_catalog_hint

logger = logging.getLogger(__name__)

MAX_REPAIR = 1


class FactExtractionAgent:
    """Silent specialist: extract vault candidates only. Never writes data."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def extract_from_chat(
        self,
        *,
        user_message: str,
        user_message_id: str,
        catalog_hint: str | None = None,
    ) -> list[VaultCandidate]:
        hint = catalog_hint or extraction_catalog_hint()
        prompt = render_template(
            "fact_extraction.v1.jinja2",
            message_id=user_message_id,
            user_message=user_message,
            source_type="chat",
            catalog_hint=hint,
        )
        result = await self._run_structured(prompt)
        for c in result.fact_candidates:
            c.source_type = "chat"
            if not c.source_reference:
                c.source_reference = user_message_id
        return result.fact_candidates

    async def extract_from_document(
        self,
        *,
        document_id: str,
        document_text: str,
        document_type_hint: str = "generic",
    ) -> list[VaultCandidate]:
        hint = (
            f"{extraction_catalog_hint()}\n\nDocument type hint: {document_type_hint}"
            if document_type_hint
            else extraction_catalog_hint()
        )
        prompt = render_template(
            "fact_extraction.v1.jinja2",
            message_id=document_id,
            user_message=document_text,
            source_type="document",
            catalog_hint=hint,
        )
        result = await self._run_structured(prompt)
        for c in result.fact_candidates:
            c.source_type = "document"
            if not c.source_reference:
                c.source_reference = document_id
        return result.fact_candidates

    async def _run_structured(self, user_prompt: str) -> FactExtractionResult:
        last_err: Exception | None = None
        for attempt in range(MAX_REPAIR + 1):
            try:
                out = await self._gateway.run(
                    task="fact_extraction",
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You extract structured profile facts only. "
                                "Never write counselor replies. Return JSON only."
                            ),
                        ),
                        LLMMessage(role="user", content=user_prompt),
                    ],
                    output_schema=FactExtractionResult,
                    temperature=0.1,
                )
                assert isinstance(out, FactExtractionResult)
                return out
            except Exception as exc:
                last_err = exc
                logger.warning("Fact extraction parse attempt %s failed", attempt + 1)
        raise last_err or RuntimeError("fact extraction failed")


class StudentConversationAgent:
    """Only user-facing agent (PAI Student Counselor) with LangGraph tool loop."""

    def __init__(
        self,
        gateway: LLMGateway,
        *,
        settings: Settings | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self._gateway = gateway
        self._settings = settings or get_settings()
        self._registry = registry or build_default_registry()
        self.last_tool_trace: list[dict[str, Any]] = []

    async def respond(
        self,
        *,
        current_message: str,
        student_context_json: str,
        recent_messages_json: str = "[]",
        known_facts_json: str = "{}",
        missing_critical_fields_json: str = "[]",
        pending_confirmations_json: str = "[]",
        active_tasks_json: str = "[]",
        applied_vault_changes_json: str = "[]",
        task_results_json: str = "[]",
        semantic_memory_context: str = "",
        memory: PersonMemoryService | None = None,
        person_id: str = "",
        conversation_id: str = "",
        tool_registry: ToolRegistry | None = None,
        enable_tools: bool | None = None,
    ) -> ConversationResult:
        prompt_vars: dict[str, Any] = {
            "current_message": current_message,
            "student_context": student_context_json,
            "recent_messages": recent_messages_json,
            "known_facts": known_facts_json,
            "semantic_memory_context": semantic_memory_context or "(none)",
            "missing_critical_fields": missing_critical_fields_json,
            "pending_confirmations": pending_confirmations_json,
            "active_tasks": active_tasks_json,
            "applied_vault_changes": applied_vault_changes_json,
            "task_results": task_results_json,
        }

        use_tools = (
            enable_tools
            if enable_tools is not None
            else self._settings.enable_counselor_tools
        )
        registry = tool_registry or self._registry

        self.last_tool_trace = []
        if memory is not None and person_id and conversation_id:
            result, trace = await run_counselor_with_tools(
                gateway=self._gateway,
                settings=self._settings,
                memory=memory,
                prompt_vars=prompt_vars,
                person_id=person_id,
                conversation_id=conversation_id,
                registry=registry,
                enable_tools=use_tools and bool(registry.openai_tools()),
            )
            self.last_tool_trace = list(trace or [])
            if trace:
                logger.info("Counselor tool trace person=%s tools=%s", person_id, len(trace))
            return result

        # Fallback: structured reply without tools (tests / degraded mode)
        prompt = render_template("student_conversation.v1.jinja2", **prompt_vars)
        last_err: Exception | None = None
        for attempt in range(MAX_REPAIR + 1):
            try:
                out = await self._gateway.run(
                    task="student_conversation",
                    messages=[
                        LLMMessage(
                            role="system",
                            content=render_template("system.v1.jinja2"),
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    output_schema=ConversationResult,
                    temperature=0.4,
                )
                assert isinstance(out, ConversationResult)
                return out
            except Exception as exc:
                last_err = exc
                logger.warning("Conversation agent parse attempt %s failed", attempt + 1)
        raise last_err or RuntimeError("conversation agent failed")
