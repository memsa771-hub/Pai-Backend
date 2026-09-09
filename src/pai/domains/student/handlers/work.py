from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Person, WorkExperience
from pai.domains.student.person.typed_resources import SCOPE_BY_RESOURCE
from pai.domains.student.vault.service import expand_scope_for_person
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import _log_typed_history, _parse_date

async def _upsert_work(
    session: AsyncSession, person: Person, items: list[Any], candidate: VaultCandidate
) -> str:
    existing = await session.execute(
        select(WorkExperience).where(WorkExperience.person_id == person.id)
    )
    known = {
        (row.organization.strip().lower(), row.title.strip().lower()): row
        for row in existing.scalars()
        if row.organization and row.title
    }
    status = "rejected"
    for raw in items:
        if not isinstance(raw, dict):
            continue
        org = str(raw.get("organization") or raw.get("company") or "").strip()
        title = str(raw.get("title") or raw.get("role") or "").strip()
        if not org or not title:
            continue
        key = (org.lower(), title.lower())
        desc = raw.get("description")
        emp = raw.get("employment_type") or raw.get("employmentType")
        current = bool(raw.get("is_current") or raw.get("isCurrent") or raw.get("current"))
        start = _parse_date(raw.get("start_date") or raw.get("startDate"))
        end = _parse_date(raw.get("end_date") or raw.get("endDate"))
        if key in known:
            row = known[key]
            if desc and not row.description:
                row.description = str(desc)
            if emp and not row.employment_type:
                row.employment_type = str(emp)[:64]
            row.is_current = current or row.is_current
            if start and not row.start_date:
                row.start_date = start
            if end and not row.end_date:
                row.end_date = end
            status = "updated" if status != "accepted" else status
            continue
        row = WorkExperience(
            person_id=person.id,
            organization=org[:256],
            title=title[:256],
            employment_type=str(emp)[:64] if emp else None,
            is_current=current,
            description=str(desc) if desc else None,
            start_date=start,
            end_date=end,
        )
        session.add(row)
        known[key] = row
        status = "accepted"
    if status != "rejected":
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["work_experiences"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value=status,
            candidate=candidate,
        )
    return status


