from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Person, Project
from pai.domains.student.person.typed_resources import SCOPE_BY_RESOURCE
from pai.domains.student.vault.service import expand_scope_for_person
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import _log_typed_history

async def _upsert_projects(
    session: AsyncSession, person: Person, items: list[Any], candidate: VaultCandidate
) -> str:
    existing = await session.execute(select(Project).where(Project.person_id == person.id))
    known = {row.name.strip().lower(): row for row in existing.scalars() if row.name}
    status = "rejected"
    for raw in items:
        if isinstance(raw, str):
            name, role, desc, url = raw.strip(), None, None, None
        elif isinstance(raw, dict):
            name = str(raw.get("name") or raw.get("title") or "").strip()
            role = raw.get("role")
            desc = raw.get("description")
            url = raw.get("url")
        else:
            continue
        if not name:
            continue
        key = name.lower()
        if key in known:
            row = known[key]
            if role and not row.role:
                row.role = str(role)[:128]
            if desc and not row.description:
                row.description = str(desc)
            if url and not row.url:
                row.url = str(url)[:512]
            status = "updated" if status != "accepted" else status
            continue
        row = Project(
            person_id=person.id,
            name=name[:256],
            role=str(role)[:128] if role else None,
            description=str(desc) if desc else None,
            url=str(url)[:512] if url else None,
        )
        session.add(row)
        known[key] = row
        status = "accepted"
    if status != "rejected":
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["projects"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value=status,
            candidate=candidate,
        )
    return status


