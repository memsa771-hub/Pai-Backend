"""Conversation continuity: omit conversationId continues latest active thread."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from auth_service.conversations.service import resolve_chat_conversation
from auth_service.orchestration.context import build_known_facts


def test_known_facts_lists_education_and_country():
    facts = build_known_facts(
        identity={"fullName": "Musawir"},
        sparse={
            "application.study_country": {"value": "Germany, China"},
            "finance.funding_status": {"value": "limited budget"},
            "preferences.learning_style": {"value": "project-based"},
        },
        typed={
            "educations": [
                {
                    "degree": "BCSS",
                    "institution": "Bahria",
                    "gpa": 3.35,
                    "gpaScale": 4.0,
                }
            ],
            "goals": [{"title": "MS in CS, AI, or Cyber"}],
            "skills": [{"name": "Python"}],
        },
    )
    joined = " | ".join(facts)
    assert "Musawir" in joined
    assert "3.35" in joined
    assert "Germany" in joined
    assert "MS in CS" in joined
    assert "limited budget" in joined
    assert "project-based" in joined
    assert "Python" in joined


@pytest.mark.asyncio
async def test_resolve_chat_continues_latest(postgres_ready):
    from auth_service.core.provider import ProviderUser
    from auth_service.data.db import get_session_factory, reset_engine_for_tests
    from auth_service.person.models import Person
    from auth_service.person.service import PersonBootstrapService

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    user = ProviderUser(
        id=f"cont-{uuid.uuid4()}",
        email="cont@example.com",
        email_verified=True,
        display_name=None,
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    async with factory() as session:
        boot = await PersonBootstrapService(postgres_ready).bootstrap(session, user)
        person = await session.get(Person, uuid.UUID(boot["person"]["id"]))
        assert person is not None
        first = await resolve_chat_conversation(
            session, person, conversation_id=None, new_conversation=True, title="A"
        )
        second = await resolve_chat_conversation(
            session, person, conversation_id=None, new_conversation=False
        )
        assert second.id == first.id
        third = await resolve_chat_conversation(
            session, person, conversation_id=None, new_conversation=True, title="B"
        )
        assert third.id != first.id
