"""Typed catalog candidate application (education GPA, passport, goals)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from pai.ingestion.vault_apply import process_candidates
from pai.orchestration.schemas import VaultCandidate
from pai.person.models import Education, Person, VaultValue


@pytest.mark.asyncio
async def test_education_gpa_typed_apply(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.person.service import PersonBootstrapService
    from pai.core.provider import ProviderUser

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    user = ProviderUser(
        id=f"typed-{uuid.uuid4()}",
        email="typed@example.com",
        email_verified=True,
        display_name=None,
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    async with factory() as session:
        boot = await PersonBootstrapService(postgres_ready).bootstrap(session, user)
        person_id = uuid.UUID(boot["person"]["id"])
        person = await session.get(Person, person_id)
        assert person is not None
        await session.refresh(person, attribute_names=["vault"])
        candidate = VaultCandidate(
            field_key="education.gpa",
            value={
                "institution": "Bahria University",
                "degree": "BS Computer Science",
                "gpa": 3.4,
            },
            confidence=0.92,
            evidence_text="BS Computer Science from Bahria University with a 3.4 CGPA",
            source_reference=str(uuid.uuid4()),
            source_type="chat",
        )
        outcomes, pending = await process_candidates(session, person, [candidate])
        await session.commit()
        assert outcomes[0].field_key == "education.gpa"
        assert outcomes[0].status in ("accepted", "updated")
        result = await session.execute(
            select(Education).where(
                Education.person_id == person.id,
                Education.institution == "Bahria University",
            )
        )
        edu = result.scalar_one()
        assert edu.gpa == 3.4

        correction = VaultCandidate(
            field_key="education.gpa",
            value={"institution": "Bahria University", "gpa": 3.6},
            confidence=0.95,
            evidence_text="Correction, my final CGPA is 3.6.",
            source_reference=str(uuid.uuid4()),
            source_type="chat",
        )
        await process_candidates(session, person, [correction])
        await session.commit()
        await session.refresh(edu)
        assert edu.gpa == 3.6


@pytest.mark.asyncio
async def test_passport_pending_sensitive(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests
    from pai.person.service import PersonBootstrapService
    from pai.core.provider import ProviderUser

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    user = ProviderUser(
        id=f"pass-{uuid.uuid4()}",
        email="pass@example.com",
        email_verified=True,
        display_name=None,
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    async with factory() as session:
        boot = await PersonBootstrapService(postgres_ready).bootstrap(session, user)
        person = await session.get(Person, uuid.UUID(boot["person"]["id"]))
        assert person is not None
        await session.refresh(person, attribute_names=["vault"])
        candidate = VaultCandidate(
            field_key="mobility.passport_number",
            value="AB123456",
            confidence=0.99,
            evidence_text="My passport number is AB123456.",
            source_reference=str(uuid.uuid4()),
            requires_confirmation=True,
        )
        outcomes, pending = await process_candidates(session, person, [candidate])
        await session.commit()
        assert outcomes[0].status == "pending"
        assert pending
        result = await session.execute(
            select(VaultValue).where(
                VaultValue.vault_id == person.vault.id,
                VaultValue.field_key == "mobility.passport_number",
                VaultValue.status == "pending_confirmation",
            )
        )
        row = result.scalar_one()
        assert row.value_encrypted is not None
        assert row.value is None
