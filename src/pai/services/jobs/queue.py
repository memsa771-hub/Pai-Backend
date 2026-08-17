from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pai.orchestration.schemas import TaskProposal
from pai.services.jobs.models import PersonJob

MAX_ATTEMPTS = 3
# ponytail: 10m lease is enough for one extract LLM call; Temporal replaces this later.
LEASE_SECONDS = 600


def _proposals_payload(proposals: list) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in proposals or []:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        elif isinstance(item, dict):
            out.append(item)
    return out


def proposals_from_payload(raw: list | None) -> list[TaskProposal]:
    return [TaskProposal.model_validate(item) for item in (raw or [])]


def needs_intelligence(*, extraction_required: bool, task_proposals: list | None) -> bool:
    return bool(extraction_required) or bool(task_proposals)


def enqueue_intelligence(
    session: AsyncSession,
    *,
    person_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_message: str,
    user_message_id: str,
    extraction_required: bool,
    task_proposals: list | None,
    run_id: str | None,
) -> PersonJob | None:
    """Stage a job on this session. Caller commits (same txn as the assistant message)."""
    if not needs_intelligence(
        extraction_required=extraction_required, task_proposals=task_proposals
    ):
        return None
    job = PersonJob(
        person_id=person_id,
        conversation_id=conversation_id,
        kind="chat_intelligence",
        status="pending",
        payload={
            "user_message": user_message,
            "user_message_id": user_message_id,
            "extraction_required": bool(extraction_required),
            "task_proposals": _proposals_payload(task_proposals),
            "run_id": run_id,
        },
    )
    session.add(job)
    return job


async def reclaim_expired_leases(session: AsyncSession) -> None:
    cutoff = datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS)
    await session.execute(
        update(PersonJob)
        .where(PersonJob.status == "processing", PersonJob.locked_at <= cutoff)
        .values(status="pending", locked_at=None)
    )


async def claim_next_person_job(session: AsyncSession) -> PersonJob | None:
    """Oldest pending job whose student is not already being processed."""
    await reclaim_expired_leases(session)
    now = datetime.now(UTC)
    busy = select(PersonJob.person_id).where(PersonJob.status == "processing")
    result = await session.execute(
        select(PersonJob)
        .where(
            PersonJob.status == "pending",
            PersonJob.available_at <= now,
            PersonJob.person_id.not_in(busy),
        )
        .order_by(PersonJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        await session.commit()
        return None
    job.status = "processing"
    job.locked_at = now
    job.attempts += 1
    await session.commit()
    await session.refresh(job)
    return job


async def mark_job_done(session: AsyncSession, job: PersonJob) -> None:
    job.status = "completed"
    job.locked_at = None
    await session.commit()


async def mark_job_failed(session: AsyncSession, job: PersonJob, exc: BaseException) -> None:
    job.last_error = str(exc)[:500]
    job.locked_at = None
    if job.attempts < MAX_ATTEMPTS:
        job.status = "pending"
        job.available_at = datetime.now(UTC) + timedelta(seconds=2**job.attempts)
    else:
        job.status = "failed"
    await session.commit()
