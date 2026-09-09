from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Certification, Person
from pai.domains.student.person.typed_resources import SCOPE_BY_RESOURCE
from pai.domains.student.vault.service import expand_scope_for_person
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import _log_typed_history

async def _upsert_certs(
    session: AsyncSession, person: Person, items: list[Any], candidate: VaultCandidate
) -> str:
    existing = await session.execute(
        select(Certification).where(Certification.person_id == person.id)
    )
    known = {row.name.strip().lower(): row for row in existing.scalars() if row.name}
    status = "rejected"
    for raw in items:
        if isinstance(raw, str):
            name, issuer = raw.strip(), None
        elif isinstance(raw, dict):
            name = str(raw.get("name") or raw.get("title") or "").strip()
            issuer = raw.get("issuer")
        else:
            continue
        if not name:
            continue
        key = name.lower()
        if key in known:
            if issuer and not known[key].issuer:
                known[key].issuer = str(issuer)[:256]
                status = "updated" if status != "accepted" else status
            continue
        row = Certification(
            person_id=person.id,
            name=name[:256],
            issuer=str(issuer)[:256] if issuer else None,
        )
        session.add(row)
        known[key] = row
        status = "accepted"
    if status != "rejected":
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["certifications"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value=status,
            candidate=candidate,
        )
    return status


