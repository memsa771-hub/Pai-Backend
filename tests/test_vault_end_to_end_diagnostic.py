"""One FSc fact through gate → write → evidence → history → snapshot.

Intelligence extraction is injected as a VaultCandidate (no live LLM).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from pai.domains.student.person.models import Education, Person, VaultEvidence, VaultHistory
from pai.domains.student.person.profile_snapshot import load_typed_profile_records
from pai.intelligences.vault.normalize import normalize_candidates
from pai.kernel.contracts.schemas import VaultCandidate
from pai.kernel.evidence.vault_apply import process_candidates

INPUT = "I completed FSc Pre-Medical at Punjab College with 877/1100 in 2024."


@pytest.mark.asyncio
async def test_fsc_fact_trace(postgres_ready):
    from pai.domains.student.person.service import PersonBootstrapService
    from pai.platform.database.db import get_session_factory, reset_engine_for_tests
    from pai.platform.security.auth.provider import ProviderUser

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    source_reference = str(uuid.uuid4())
    user = ProviderUser(
        id=f"diag-{uuid.uuid4()}",
        email=f"diag-{uuid.uuid4().hex[:8]}@example.com",
        email_verified=True,
        display_name=None,
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    raw = [
        VaultCandidate(
            field_key="education.program",
            value={
                "degree": "FSc",
                "major": "Pre-Medical",
                "institution": "Punjab College",
                "marks_obtained": 877,
                "marks_total": 1100,
                "graduation_year": 2024,
            },
            confidence=0.95,
            evidence_text=INPUT,
            source_reference=source_reference,
            source_type="chat",
            assertion_status="explicit",
        ),
        VaultCandidate(
            field_key="education.highest_level",
            value="high_school",
            confidence=0.9,
            evidence_text=INPUT,
            source_reference=source_reference,
            source_type="chat",
            assertion_status="explicit",
        ),
    ]
    normalized = normalize_candidates(raw)
    async with factory() as session:
        boot = await PersonBootstrapService(postgres_ready).bootstrap(session, user)
        person = await session.get(Person, uuid.UUID(boot["person"]["id"]))
        assert person is not None
        await session.refresh(person, attribute_names=["vault"])
        outcomes, _ = await process_candidates(session, person, normalized)
        await session.commit()
        edu = (await session.execute(select(Education).where(Education.person_id == person.id))).scalar_one()
        evidence = (
            await session.execute(
                select(VaultEvidence).where(
                    VaultEvidence.entity_type == "education",
                    VaultEvidence.entity_id == edu.id,
                )
            )
        ).scalars().all()
        history = (
            await session.execute(
                select(VaultHistory).where(
                    VaultHistory.vault_id == person.vault.id,
                    VaultHistory.field_key == "education.program",
                )
            )
        ).scalars().all()
        typed = await load_typed_profile_records(session, person.id)

    trace = {
        "input": INPUT,
        "source_reference": source_reference,
        "normalized_candidates": [c.field_key for c in normalized],
        "gate_results": [{"field_key": o.field_key, "status": o.status} for o in outcomes],
        "db_state": {
            "degree": edu.degree,
            "major": edu.major,
            "institution": edu.institution,
            "percentage": edu.percentage,
            "graduation_year": edu.graduation_year,
        },
        "evidence_attributes": sorted({row.attribute for row in evidence if row.attribute}),
        "history_actions": [row.action for row in history],
        "snapshot": typed["educations"][0] if typed.get("educations") else {},
    }
    assert trace["normalized_candidates"] == ["education.program"]
    assert trace["gate_results"][0]["status"] in ("accepted", "updated")
    assert trace["db_state"]["degree"] == "FSc"
    assert trace["db_state"]["institution"] == "Punjab College"
    assert trace["db_state"]["percentage"] == pytest.approx(79.73, abs=0.05)
    assert "institution" in trace["evidence_attributes"]
    assert "created" in trace["history_actions"]
    assert trace["snapshot"]["major"] == "Pre-Medical"


@pytest.mark.asyncio
async def test_bootstrap_same_email_new_auth_id_reuses_person(postgres_ready):
    from pai.domains.student.person.service import PersonBootstrapService
    from pai.platform.database.db import get_session_factory, reset_engine_for_tests
    from pai.platform.security.auth.provider import ProviderUser

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)
    email = f"rebind-{uuid.uuid4().hex[:8]}@example.com"
    first = ProviderUser(
        id=f"auth-a-{uuid.uuid4()}",
        email=email,
        email_verified=True,
        display_name="One",
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    second = ProviderUser(
        id=f"auth-b-{uuid.uuid4()}",
        email=email,
        email_verified=True,
        display_name="One",
        roles=["user"],
        created_at="2026-01-01T00:00:00Z",
    )
    async with factory() as session:
        a = await PersonBootstrapService(postgres_ready).bootstrap(session, first)
        b = await PersonBootstrapService(postgres_ready).bootstrap(session, second)
    assert a["person"]["id"] == b["person"]["id"]
    assert a["vault"]["id"] == b["vault"]["id"]
