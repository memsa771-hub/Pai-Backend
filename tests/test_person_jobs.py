from __future__ import annotations

import asyncio
import uuid

from pai.orchestration.schemas import TaskProposal
from pai.services.jobs.queue import (
    claim_next_person_job,
    enqueue_intelligence,
    needs_intelligence,
)
from pai.services.person.models import Person


def test_needs_intelligence_skips_greetings():
    assert needs_intelligence(extraction_required=False, task_proposals=[]) is False
    assert needs_intelligence(extraction_required=True, task_proposals=[]) is True
    assert needs_intelligence(
        extraction_required=False, task_proposals=[TaskProposal(title="Prep IELTS")]
    ) is True


def test_claim_serializes_one_student(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.services.conversations.models import Conversation

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _run():
        async with factory() as session:
            a = Person(
                auth_provider="supabase",
                external_auth_id=f"job-a-{uuid.uuid4()}",
                email=f"job-a-{uuid.uuid4()}@example.com",
            )
            b = Person(
                auth_provider="supabase",
                external_auth_id=f"job-b-{uuid.uuid4()}",
                email=f"job-b-{uuid.uuid4()}@example.com",
            )
            session.add_all([a, b])
            await session.flush()
            conv_a = Conversation(person_id=a.id, title="PAI")
            conv_b = Conversation(person_id=b.id, title="PAI")
            session.add_all([conv_a, conv_b])
            await session.flush()
            enqueue_intelligence(
                session,
                person_id=a.id,
                conversation_id=conv_a.id,
                user_message="I want Germany",
                user_message_id=str(uuid.uuid4()),
                extraction_required=True,
                task_proposals=[],
                run_id=None,
            )
            enqueue_intelligence(
                session,
                person_id=a.id,
                conversation_id=conv_a.id,
                user_message="Actually France",
                user_message_id=str(uuid.uuid4()),
                extraction_required=True,
                task_proposals=[],
                run_id=None,
            )
            enqueue_intelligence(
                session,
                person_id=b.id,
                conversation_id=conv_b.id,
                user_message="I live in Berlin",
                user_message_id=str(uuid.uuid4()),
                extraction_required=True,
                task_proposals=[],
                run_id=None,
            )
            await session.commit()
            first = await claim_next_person_job(session)
            assert first is not None
            assert first.payload["user_message"] == "I want Germany"
            second = await claim_next_person_job(session)
            assert second is not None
            assert second.person_id == b.id
            third = await claim_next_person_job(session)
            assert third is None

    asyncio.run(_run())
