from __future__ import annotations

import inspect
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pai.llm.gateway import LLMGateway
from pai.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from pai.orchestration.agents import FactExtractionAgent, StudentConversationAgent
from pai.orchestration.orchestrator import PAIOrchestrator, counselor_web_search_enabled
from pai.orchestration.routing import should_extract_facts
from pai.orchestration.schemas import (
    ConversationResult,
    FactExtractionResult,
    TaskProposal,
    VaultCandidate,
)
from pai.orchestration.candidate_eval import evaluate_candidate_with_context
from pai.orchestration.verifier import validate_candidate


class SchemaRoutingMockProvider:
    name = "mock"

    def __init__(
        self,
        *,
        extraction: FactExtractionResult | None = None,
        conversation: ConversationResult | None = None,
    ) -> None:
        self.extraction = extraction or FactExtractionResult()
        self.conversation = conversation or ConversationResult(
            reply="Hello from PAI Student Counselor.",
            next_question="What are you studying?",
        )
        self.calls: list[str] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="ok", provider=self.name, model="mock")

    async def generate_structured(self, request: LLMRequest, output_schema: type) -> Any:
        self.calls.append(output_schema.__name__)
        if output_schema.__name__ == "FactExtractionResult":
            return self.extraction
        if output_schema.__name__ == "ConversationResult":
            return self.conversation
        raise ValueError(f"unexpected schema {output_schema.__name__}")


def test_greetings_skip_extraction():
    assert should_extract_facts("Hello") is False
    assert should_extract_facts("Thanks!") is False
    assert should_extract_facts("Please continue") is False


def test_web_search_follows_tavily_config_not_keywords(test_settings):
    off = test_settings.model_copy(update={"tavily_api_key": "", "enable_counselor_tools": True})
    assert counselor_web_search_enabled(off) is False
    on = test_settings.model_copy(
        update={"tavily_api_key": "tvly-test", "enable_counselor_tools": True}
    )
    assert counselor_web_search_enabled(on) is True
    killed = test_settings.model_copy(
        update={"tavily_api_key": "tvly-test", "enable_counselor_tools": False}
    )
    assert counselor_web_search_enabled(killed) is False


def test_substantive_messages_trigger_extraction():
    assert should_extract_facts("I completed BSCS with a 3.4 GPA.") is True
    assert should_extract_facts("I want to study AI in Germany.") is True
    assert should_extract_facts("My budget is approximately 20,000 euros.") is True
    assert should_extract_facts("PRE MEDICAL 877/1100") is True
    assert should_extract_facts("I want FAST or NUST in Islamabad") is True
    assert should_extract_facts("I live in Dubai and want NYU Abu Dhabi") is True
    assert should_extract_facts("I live in Berlin") is True
    assert should_extract_facts("I moved last month") is True
    assert should_extract_facts("Hello") is False


def test_agents_do_not_call_each_other():
    assert "FactExtractionAgent" not in inspect.getsource(StudentConversationAgent)
    assert "StudentConversationAgent" not in inspect.getsource(FactExtractionAgent)
    fact_src = inspect.getsource(FactExtractionAgent.extract_from_chat)
    assert "conversation" not in fact_src.lower() or "Never write counselor" in fact_src


def test_only_conversation_agent_sets_reply(test_settings):
    gateway = LLMGateway(test_settings)
    gateway.register_provider("deepseek", SchemaRoutingMockProvider())
    conv = StudentConversationAgent(gateway)
    import asyncio

    result = asyncio.run(
        conv.respond(
            current_message="Hi",
            student_context_json="{}",
            recent_messages_json="[]",
            known_facts_json="{}",
            missing_critical_fields_json="[]",
            pending_confirmations_json="[]",
            active_tasks_json="[]",
            applied_vault_changes_json="[]",
            task_results_json="[]",
        )
    )
    assert "Hello from PAI" in result.reply


def test_fact_agent_returns_empty_without_reply(test_settings):
    gateway = LLMGateway(test_settings)
    gateway.register_provider("deepseek", SchemaRoutingMockProvider())
    fact = FactExtractionAgent(gateway)
    import asyncio

    out = asyncio.run(
        fact.extract_from_chat(user_message="Hello", user_message_id="mid-1")
    )
    assert out == []


def test_invalid_llm_field_rejected_before_vault():
    bad = VaultCandidate(
        field_key="not.real.field",
        value="x",
        confidence=0.99,
        evidence_text="text",
        source_reference=str(uuid.uuid4()),
    )
    assert validate_candidate(bad) is None


@pytest.mark.asyncio
async def test_evaluate_sensitive_pending(postgres_ready, test_settings):
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.person.models import Person, PersonVault

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    async with factory() as session:
        person = Person(
            auth_provider="supabase",
            external_auth_id="sens-user",
            email="sens@example.com",
        )
        session.add(person)
        await session.flush()
        session.add(
            PersonVault(
                person_id=person.id,
                catalog_version="1",
                applicable_scopes=["student"],
            )
        )
        await session.commit()
        await session.refresh(person, attribute_names=["vault"])
        cand = VaultCandidate(
            field_key="demographics.date_of_birth",
            value="2000-01-01",
            confidence=0.92,
            evidence_text="born 2000",
            source_reference="m1",
            requires_confirmation=True,
            explicitness="explicit",
        )
        result = await evaluate_candidate_with_context(session, person, cand)
        assert result.outcome == "pending_confirmation"


def test_orchestrator_wires_agents(test_settings):
    gateway = LLMGateway(test_settings)
    mock = SchemaRoutingMockProvider(
        extraction=FactExtractionResult(
            fact_candidates=[
                VaultCandidate(
                    field_key="preferences.preferred_language",
                    value="en",
                    confidence=0.92,
                    evidence_text="English",
                    source_reference="msg-1",
                    explicitness="explicit",
                )
            ]
        ),
        conversation=ConversationResult(
            reply="Noted.",
            next_question="Target country?",
            task_proposals=[TaskProposal(title="Prepare IELTS timeline")],
        ),
    )
    gateway.register_provider("deepseek", mock)
    orch = PAIOrchestrator(test_settings, gateway=gateway)
    assert orch._fact_agent is not None
    assert orch._conversation_agent is not None
    assert "FactExtractionAgent" in type(orch._fact_agent).__name__
    assert "StudentConversationAgent" in type(orch._conversation_agent).__name__


def test_mock_provider_replace_deepseek(test_settings):
    gateway = LLMGateway(test_settings)
    gateway.register_provider("deepseek", SchemaRoutingMockProvider())
    import asyncio

    out = asyncio.run(
        gateway.run(
            task="student_conversation",
            messages=[LLMMessage(role="user", content="x")],
            output_schema=ConversationResult,
        )
    )
    assert isinstance(out, ConversationResult)


def test_llm_call_budget_constants():
    from pai.orchestration.orchestrator import MAX_LLM_CALLS_PER_TURN

    assert MAX_LLM_CALLS_PER_TURN == 2


def test_chat_message_id_used_as_evidence(test_settings):
    gateway = LLMGateway(test_settings)
    mock = SchemaRoutingMockProvider(
        extraction=FactExtractionResult(
            fact_candidates=[
                VaultCandidate(
                    field_key="preferences.preferred_language",
                    value="en",
                    confidence=0.92,
                    evidence_text="English please",
                    source_reference="",
                    explicitness="explicit",
                )
            ]
        ),
        conversation=ConversationResult(reply="Thanks.", next_question="Next?"),
    )
    gateway.register_provider("deepseek", mock)
    fact = FactExtractionAgent(gateway)
    import asyncio

    cands = asyncio.run(
        fact.extract_from_chat(user_message="English please", user_message_id="exact-msg-id")
    )
    assert cands[0].source_reference == "exact-msg-id"


def test_vault_candidate_fields_roundtrip():
    c = VaultCandidate(
        field_key="preferences.preferred_language",
        value="en",
        confidence=0.9,
        evidence_text="e",
        source_reference="m",
        rationale_summary="r",
    )
    assert c.field_key == "preferences.preferred_language"
    assert c.rationale_summary == "r"


def test_duplicate_tasks_prevented(postgres_ready, test_settings):
    import asyncio
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.person.models import Person
    from pai.tasks.service import process_task_proposals
    from pai.orchestration.schemas import TaskProposal

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _run():
        async with factory() as session:
            person = Person(
                auth_provider="supabase",
                external_auth_id="task-user",
                email="task@example.com",
            )
            session.add(person)
            await session.commit()
            props = [
                TaskProposal(title="Prepare IELTS timeline"),
                TaskProposal(title="Prepare IELTS timeline"),
            ]
            r1 = await process_task_proposals(session, person, props)
            await session.commit()
            assert r1[0].status == "proposed"
            assert r1[1].status == "duplicate"

    asyncio.run(_run())


def test_substantive_turn_calls_extraction_then_conversation(test_settings):
    gateway = LLMGateway(test_settings)
    mock = SchemaRoutingMockProvider(
        extraction=FactExtractionResult(fact_candidates=[]),
        conversation=ConversationResult(reply="Got it."),
    )
    gateway.register_provider("deepseek", mock)
    import asyncio

    fact = FactExtractionAgent(gateway)
    conv = StudentConversationAgent(gateway)
    asyncio.run(fact.extract_from_chat(user_message="I have a 3.4 GPA", user_message_id="m1"))
    asyncio.run(
        conv.respond(
            current_message="I have a 3.4 GPA",
            student_context_json="{}",
            recent_messages_json="[]",
            known_facts_json="{}",
            missing_critical_fields_json="[]",
            pending_confirmations_json="[]",
            active_tasks_json="[]",
            applied_vault_changes_json="[]",
            task_results_json="[]",
        )
    )
    assert mock.calls == ["FactExtractionResult", "ConversationResult"]

