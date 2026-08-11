from __future__ import annotations

import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from auth_service.llm.gateway import LLMGateway
from auth_service.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from auth_service.llm.providers.deepseek import LLMProviderError
from auth_service.orchestration.prompts import render_template, validate_prompt_templates
from auth_service.orchestration.schemas import ConversationResult, FactExtractionResult, VaultCandidate
from auth_service.orchestration.verifier import policy_decision, validate_candidate


class RecordingMockProvider:
    name = "mock"

    def __init__(self, structured: BaseModel | None = None, *, fail: bool = False) -> None:
        self.structured = structured
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append({"type": "generate", "messages": len(request.messages)})
        if self.fail:
            raise LLMProviderError("fail")
        return LLMResponse(content="ok", provider=self.name, model="mock-1")

    async def generate_structured(
        self, request: LLMRequest, output_schema: type[BaseModel]
    ) -> BaseModel:
        self.calls.append({"type": "structured", "schema": output_schema.__name__})
        if self.fail:
            raise LLMProviderError("fail")
        if self.structured is not None:
            return self.structured
        return ConversationResult(
            reply="Hello from mock counselor.",
            next_question=None,
        )


def test_prompt_templates_validate_at_startup():
    validate_prompt_templates()


def test_prompt_render_student_conversation():
    text = render_template(
        "student_conversation.v1.jinja2",
        current_message="Hi",
        student_context="{}",
        recent_messages="[]",
        known_facts="{}",
        semantic_memory_context="(none)",
        missing_critical_fields="[]",
        pending_confirmations="[]",
        active_tasks="[]",
        applied_vault_changes="[]",
        task_results="[]",
    )
    assert "PAI" in text or "student" in text.lower()
    extract = render_template(
        "fact_extraction.v1.jinja2",
        message_id="msg-1",
        user_message="My GPA is 3.9",
        source_type="chat",
        catalog_hint="",
    )
    assert "msg-1" in extract


def test_gateway_uses_registered_mock_provider(test_settings):
    gateway = LLMGateway(test_settings)
    mock = RecordingMockProvider(
        structured=ConversationResult(reply="R", next_question="Q?")
    )
    gateway.register_provider("deepseek", mock)
    import asyncio

    result = asyncio.run(
        gateway.run(
            task="counseling",
            messages=[LLMMessage(role="user", content="x")],
            output_schema=ConversationResult,
        )
    )
    assert isinstance(result, ConversationResult)
    assert result.reply == "R"
    assert mock.calls


def test_gateway_provider_switch_without_changing_orchestration(test_settings):
    gateway = LLMGateway(test_settings)
    first = RecordingMockProvider(structured=ConversationResult(reply="A"))
    second = RecordingMockProvider(structured=ConversationResult(reply="B"))
    gateway.register_provider("deepseek", first)
    gateway.register_provider("other", second)
    import asyncio

    out_a = asyncio.run(
        gateway.run(
            task="counseling",
            messages=[LLMMessage(role="user", content="1")],
            output_schema=ConversationResult,
        )
    )
    gateway._settings.llm_default_provider = "other"
    out_b = asyncio.run(
        gateway.run(
            task="student_conversation",
            messages=[LLMMessage(role="user", content="2")],
            output_schema=ConversationResult,
        )
    )
    assert out_a.reply == "A"
    assert out_b.reply == "B"


def test_deepseek_invalid_structured_json(test_settings, monkeypatch):
    from auth_service.llm.providers.deepseek import DeepSeekProvider

    settings = test_settings.model_copy(update={"deepseek_api_key": "test-key"})
    provider = DeepSeekProvider(settings)

    async def fake_post(*args, **kwargs):
        class Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "not-json"}}], "usage": {}}

        return Resp()

    monkeypatch.setattr(provider._client, "post", fake_post)
    import asyncio

    with pytest.raises(LLMProviderError):
        asyncio.run(
            provider.generate_structured(
                LLMRequest(messages=[LLMMessage(role="user", content="x")]),
                ConversationResult,
            )
        )


def test_validate_candidate_requires_catalog_and_evidence():
    good = VaultCandidate(
        field_key="preferences.preferred_language",
        value="en",
        confidence=0.95,
        evidence_text="I prefer English",
        source_reference=str(uuid.uuid4()),
    )
    assert validate_candidate(good) is not None
    bad = VaultCandidate(
        field_key="not.real",
        value="x",
        confidence=0.9,
        evidence_text="x",
        source_reference="1",
    )
    assert validate_candidate(bad) is None


def test_policy_sensitive_requires_confirmation():
    sensitive = VaultCandidate(
        field_key="demographics.date_of_birth",
        value="2000-01-01",
        confidence=0.9,
        evidence_text="born 2000",
        source_reference="m1",
        requires_confirmation=True,
    )
    assert policy_decision(sensitive) == "pending"


def test_chat_message_with_mock_counselor(verified_user, test_settings, monkeypatch):
    from tests.test_pai_orchestration import SchemaRoutingMockProvider
    from auth_service.orchestration.orchestrator import PAIOrchestrator
    from auth_service.orchestration.schemas import VaultCandidate as OrchVaultCandidate

    client, headers, _ = verified_user
    client.post("/api/v1/person/bootstrap", headers=headers)
    conv_id = client.post("/api/v1/conversations", headers=headers, json={}).json()["data"]["id"]

    mock = SchemaRoutingMockProvider(
        extraction=FactExtractionResult(
            fact_candidates=[
                OrchVaultCandidate(
                    field_key="preferences.preferred_language",
                    value="en",
                    confidence=0.92,
                    evidence_text="I prefer English for counseling.",
                    source_reference="",
                    explicitness="explicit",
                )
            ]
        ),
        conversation=ConversationResult(
            reply="Thanks — noted your language preference.",
            next_question="What field are you targeting?",
        ),
    )
    gateway = LLMGateway(test_settings)
    gateway.register_provider("deepseek", mock)
    orchestrator = PAIOrchestrator(test_settings, gateway=gateway)
    monkeypatch.setattr(
        "auth_service.ingestion.chat.PAIOrchestrator",
        lambda settings, gateway=None: orchestrator,
    )
    resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "I prefer English for counseling."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["reply"]
    assert body.get("conversationId") == conv_id
    assert "nextQuestion" not in body
    assert "vaultCompletion" not in body
    field = client.get(
        "/api/v1/vault/fields/preferences.preferred_language",
        headers=headers,
    )
    assert field.status_code == 200
    assert field.json()["data"]["value"] == "en"


def test_policy_high_confidence_non_sensitive_accepts():
    c = VaultCandidate(
        field_key="preferences.preferred_language",
        value="en",
        confidence=0.9,
        evidence_text="English please",
        source_reference="m1",
    )
    assert policy_decision(c) == "accept"


def test_conversation_create_and_ownership(verified_user, test_settings):
    client, headers, _ = verified_user
    client.post("/api/v1/person/bootstrap", headers=headers)
    created = client.post("/api/v1/conversations", headers=headers, json={"title": "Plan"})
    assert created.status_code == 201
    conv_id = created.json()["data"]["id"]
    listing = client.get("/api/v1/conversations", headers=headers)
    assert any(i["id"] == conv_id for i in listing.json()["data"]["items"])
    import jwt
    from datetime import UTC, datetime, timedelta

    token = jwt.encode(
        {
            "sub": "other-user",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        test_settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    forbidden = client.get(
        f"/api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forbidden.status_code in (403, 404)


def test_document_upload_validation_rejects_executable(verified_user):
    client, headers, _ = verified_user
    client.post("/api/v1/person/bootstrap", headers=headers)
    files = {"file": ("malware.exe", b"MZ", "application/octet-stream")}
    resp = client.post("/api/v1/documents", headers=headers, files=files)
    assert resp.status_code == 400


def test_claim_job_skip_locked(postgres_ready, test_settings):
    import asyncio
    from datetime import UTC, datetime

    from auth_service.data.db import get_session_factory, reset_engine_for_tests
    from auth_service.documents.models import Document, DocumentJob
    from auth_service.documents.service import claim_next_job
    from auth_service.person.models import Person

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _setup_and_claim():
        async with factory() as session:
            person = Person(
                auth_provider="supabase",
                external_auth_id="job-user",
                email="job@example.com",
            )
            session.add(person)
            await session.flush()
            doc = Document(
                person_id=person.id,
                storage_path=f"{person.id}/doc/cv.txt",
                original_filename="cv.txt",
                mime_type="text/plain",
                size_bytes=3,
            )
            session.add(doc)
            await session.flush()
            job = DocumentJob(
                document_id=doc.id,
                person_id=person.id,
                idempotency_key=f"test-{uuid.uuid4()}",
                status="pending",
                available_at=datetime.now(UTC),
            )
            session.add(job)
            await session.commit()
            job_id = job.id
        async with factory() as session:
            j1 = await claim_next_job(session)
            assert j1 is not None
            assert j1.id == job_id
            assert j1.status == "processing"
        async with factory() as session:
            j2 = await claim_next_job(session)
            assert j2 is None

    asyncio.run(_setup_and_claim())
