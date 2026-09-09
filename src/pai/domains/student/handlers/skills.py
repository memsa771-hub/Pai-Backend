from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Person, Skill
from pai.domains.student.person.typed_resources import SCOPE_BY_RESOURCE
from pai.domains.student.vault.service import expand_scope_for_person
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import _log_typed_history

async def _upsert_skills(
    session: AsyncSession, person: Person, items: list[Any], candidate: VaultCandidate
) -> str:
    existing = await session.execute(select(Skill).where(Skill.person_id == person.id))
    known = {row.name.strip().lower(): row for row in existing.scalars() if row.name}
    status = "reinforced"
    added: list[str] = []
    for raw in items:
        if isinstance(raw, str):
            name, proficiency = raw.strip(), None
        elif isinstance(raw, dict):
            name = str(raw.get("name") or raw.get("skill") or "").strip()
            proficiency = raw.get("proficiency")
            proficiency = str(proficiency).strip() if proficiency else None
        else:
            continue
        if not name:
            continue
        key = name.lower()
        if key in known:
            if proficiency and not known[key].proficiency:
                known[key].proficiency = proficiency[:64]
                status = "updated"
            continue
        row = Skill(person_id=person.id, name=name[:128], proficiency=proficiency)
        session.add(row)
        known[key] = row
        added.append(name)
        status = "accepted"
    if added or status != "reinforced":
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["skills"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value=added or "updated",
            candidate=candidate,
        )
    return status if (added or status != "reinforced") else "rejected"


