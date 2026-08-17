from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from pai.services.journey.extract import extract_goal


def test_local_uni_is_a_goal():
    hit = extract_goal("I want to study locally in FAST")
    assert hit is not None
    assert "study locally" in hit.object_label.lower()
    assert "fast" in hit.object_label.lower()
    assert hit.stance == "pursuing"
    assert hit.object_key == "goal:now"


def test_pivot_local_to_international():
    first = extract_goal("I want to study locally in FAST")
    later = extract_goal("I want to study internationally not local")
    assert first is not None and later is not None
    assert first.object_label != later.object_label
    assert "international" in later.object_label.lower()
    assert later.reason == "pivot"


def test_considering_is_exploring_any_goal():
    hit = extract_goal("I am considering an internship in Dubai")
    assert hit is not None
    assert hit.stance == "exploring"
    assert "internship" in hit.object_label.lower()


def test_last_want_wins_in_one_message():
    hit = extract_goal("US is too expensive I want Germany")
    assert hit is not None
    assert "germany" in hit.object_label.lower()
    assert "united states" not in hit.object_label.lower()


def test_questions_and_greetings_are_not_goals():
    assert extract_goal("Hi") is None
    assert extract_goal("What universities fit my GPA?") is None
    assert extract_goal("tell us about your plans") is None


@pytest.mark.asyncio
async def test_goal_pivot_keeps_history(postgres_ready):
    from pai.auth.provider import ProviderUser
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.services.journey.extract import extract_goal
    from pai.services.journey.models import PersonDecision
    from pai.services.journey.service import apply_goal_hit, list_goal_versions
    from pai.services.person.models import Person
    from pai.services.person.service import PersonBootstrapService

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    user = ProviderUser(
        id=f"journey-{uuid.uuid4()}",
        email="journey@example.com",
        email_verified=True,
        display_name=None,
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    async with factory() as session:
        boot = await PersonBootstrapService(postgres_ready).bootstrap(session, user)
        person = await session.get(Person, uuid.UUID(boot["person"]["id"]))
        assert person is not None
        first = extract_goal("I want to study locally in FAST")
        later = extract_goal("I want to study internationally not local")
        assert first and later
        await apply_goal_hit(session, person.id, first)
        await session.commit()
        await apply_goal_hit(session, person.id, later)
        await session.commit()
        versions = await list_goal_versions(session, person.id)
        assert len(versions) == 2
        current = next(row for row in versions if row.status == "active")
        previous = next(row for row in versions if row.status == "superseded")
        assert current.version == 2
        assert "international" in current.object_label.lower()
        assert "locally" in previous.object_label.lower()
        result = await session.execute(
            select(PersonDecision).where(PersonDecision.person_id == person.id)
        )
        assert {row.status for row in result.scalars().all()} == {"active", "superseded"}
