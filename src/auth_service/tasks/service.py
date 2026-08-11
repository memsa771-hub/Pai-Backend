from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.orchestration.schemas import TaskProposal, TaskResult
from auth_service.person.models import Person
from auth_service.tasks.models import StudentTask

_ACTIVE = ("proposed", "accepted", "in_progress")


async def list_tasks_for_person(
    session: AsyncSession, person_id: uuid.UUID, *, limit: int = 30
) -> list[StudentTask]:
    result = await session.execute(
        select(StudentTask)
        .where(StudentTask.person_id == person_id, StudentTask.status.in_(_ACTIVE))
        .order_by(StudentTask.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def process_task_proposals(
    session: AsyncSession,
    person: Person,
    proposals: list[TaskProposal],
    *,
    conversation_id: uuid.UUID | None = None,
) -> list[TaskResult]:
    if not proposals:
        return []
    existing = await session.execute(
        select(StudentTask.title).where(
            StudentTask.person_id == person.id,
            StudentTask.status.in_(_ACTIVE),
        )
    )
    titles = {t.lower().strip() for t in existing.scalars().all()}
    results: list[TaskResult] = []
    for p in proposals:
        key = p.title.lower().strip()
        if not key or key in titles:
            results.append(TaskResult(title=p.title, status="duplicate", detail=p.detail))
            continue
        status = "proposed"
        if p.requires_confirmation:
            status = "proposed"
        row = StudentTask(
            person_id=person.id,
            conversation_id=conversation_id,
            title=p.title.strip(),
            detail=p.detail,
            status=status,
        )
        session.add(row)
        await session.flush()
        titles.add(key)
        results.append(
            TaskResult(title=p.title, status=status, task_id=str(row.id), detail=p.detail)
        )
    return results
