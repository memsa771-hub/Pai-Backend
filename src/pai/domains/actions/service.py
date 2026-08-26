from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.kernel.contracts.schemas import TaskProposal, TaskResult
from pai.domains.student.person.models import Person
from pai.domains.actions.models import StudentTask

_ACTIVE = ("proposed", "accepted", "in_progress")

# Tasks must be student actions (prep NET, submit app) — never "record what you just said".
_FACT_RECORDING_TASK = re.compile(
    r"^\s*(record|save|add|update|store|enter|fill\s*in|capture)\b.*"
    r"\b(education|fsc|pre[\s-]?medical|degree|gpa|marks|profile|vault|fact|goal|"
    r"information|detail|data)\b",
    re.I,
)


def is_fact_recording_task(title: str, detail: str | None = None) -> bool:
    text = f"{title} {detail or ''}".strip()
    if not text:
        return True
    if _FACT_RECORDING_TASK.search(title or ""):
        return True
    # Common LLM patterns after failed ingestion
    lowered = title.lower()
    if "record your" in lowered or "save your" in lowered or "add your" in lowered:
        return True
    return False


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
        if is_fact_recording_task(p.title, p.detail):
            results.append(
                TaskResult(
                    title=p.title,
                    status="rejected",
                    detail="Profile facts must be saved via Vault ingestion, not tasks.",
                )
            )
            continue
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
