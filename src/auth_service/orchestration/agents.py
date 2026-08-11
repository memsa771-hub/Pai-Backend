from __future__ import annotations

import json
import logging
from typing import Any

from auth_service.config import Settings, get_settings
from auth_service.intelligence.vault_intel.service import VaultIntelligenceService
from auth_service.intelligence.vault_intel.types import ExtractionBundle
from auth_service.llm.gateway import LLMGateway
from auth_service.llm.schemas import LLMMessage
from auth_service.memory.service import PersonMemoryService
from auth_service.orchestration.counselor_graph import run_counselor_with_tools
from auth_service.orchestration.prompts import render_template
from auth_service.orchestration.schemas import ConversationResult, VaultCandidate
from auth_service.tools.registry import ToolRegistry, build_default_registry

logger = logging.getLogger(__name__)

MAX_REPAIR = 1


class FactExtractionAgent:
    """Compatibility facade over VaultIntelligenceService (chat + document)."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self._intel = VaultIntelligenceService(gateway)
        self.last_bundle: ExtractionBundle | None = None

    async def extract_from_chat(
        self,
        *,
        user_message: str,
        user_message_id: str,
        catalog_hint: str | None = None,
        known_facts: list[str] | None = None,
        person_id: str | None = None,
        memory: PersonMemoryService | None = None,
    ) -> list[VaultCandidate]:
        del catalog_hint  # catalog is owned by Vault Intelligence
        intel = VaultIntelligenceService(self._gateway, memory=memory)
        bundle = await intel.extract_chat_bundle(
            user_message=user_message,
            user_message_id=user_message_id,
            known_facts=known_facts,
            person_id=person_id,
        )
        self.last_bundle = bundle
        return bundle.candidates

    async def extract_from_document(
        self,
        *,
        document_id: str,
        document_text: str,
        document_type_hint: str = "generic",
        known_facts: list[str] | None = None,
        person_id: str | None = None,
        memory: PersonMemoryService | None = None,
    ) -> list[VaultCandidate]:
        intel = VaultIntelligenceService(self._gateway, memory=memory)
        candidates = await intel.extract_from_document(
            document_id=document_id,
            document_text=document_text,
            document_type_hint=document_type_hint,
            known_facts=known_facts,
            person_id=person_id,
        )
        return candidates


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
        known_facts_lines: list[str] | None = None,
        pending_confirmations_json: str = "[]",
        applied_vault_changes_json: str = "[]",
        task_results_json: str = "[]",
        semantic_memory_context: str = "",
        memory: PersonMemoryService | None = None,
        person_id: str = "",
        conversation_id: str = "",
        tool_registry: ToolRegistry | None = None,
        enable_tools: bool | None = None,
        # Backward-compatible unused kwargs from older callers/tests
        recent_messages_json: str = "[]",
        known_facts_json: str = "{}",
        missing_critical_fields_json: str = "[]",
        active_tasks_json: str = "[]",
    ) -> ConversationResult:
        facts = known_facts_lines
        if facts is None and known_facts_json and known_facts_json not in ("{}", "[]"):
            try:
                parsed = json.loads(known_facts_json)
                if isinstance(parsed, list):
                    facts = [str(x) for x in parsed]
                elif isinstance(parsed, dict):
                    facts = [f"{k}: {v}" for k, v in parsed.items()]
            except Exception:
                facts = []
        prompt_vars: dict[str, Any] = {
            "current_message": current_message,
            "student_context": student_context_json,
            "known_facts": facts or [],
            "semantic_memory_context": semantic_memory_context or "(none)",
            "pending_confirmations": pending_confirmations_json,
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
