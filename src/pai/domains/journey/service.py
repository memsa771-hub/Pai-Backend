from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.journey.extract import GoalHit, normalize_intent, resolve_goal_hit
from pai.domains.journey.models import PersonDecision, PersonEvent

_SUMMARY_MAX = 240
_ACTIVE = "active"
_SUPERSEDED = "superseded"
_GOAL_NOW = "goal:now"


def append_event(
    session: AsyncSession,
    person_id: uuid.UUID,
    *,
    kind: str,
    summary: str,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> PersonEvent:
    row = PersonEvent(
        person_id=person_id,
        kind=kind,
        summary=(summary or "")[:_SUMMARY_MAX],
        source_type=source_type,
        source_id=source_id,
        payload=payload or {},
    )
    session.add(row)
    return row


async def apply_goal_hit(
    session: AsyncSession,
    person_id: uuid.UUID,
    hit: GoalHit,
    *,
    event_id: uuid.UUID | None = None,
) -> bool:
    result = await session.execute(
        select(PersonDecision).where(
            PersonDecision.person_id == person_id,
            PersonDecision.status == _ACTIVE,
            PersonDecision.object_key == _GOAL_NOW,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None and normalize_intent(existing.object_label) == normalize_intent(
        hit.object_label
    ):
        changed = False
        if existing.stance != hit.stance:
            existing.stance = hit.stance
            changed = True
        if hit.reason and not existing.reason:
            existing.reason = hit.reason
            changed = True
        return changed
    version = 1
    supersedes_id = None
    if existing is not None:
        existing.status = _SUPERSEDED
        version = existing.version + 1
        supersedes_id = existing.id
    session.add(
        PersonDecision(
            person_id=person_id,
            object_key=_GOAL_NOW,
            object_label=hit.object_label,
            stance=hit.stance,
            reason=hit.reason,
            evidence=hit.evidence,
            version=version,
            status=_ACTIVE,
            supersedes_id=supersedes_id,
            event_id=event_id,
        )
    )
    return True


async def apply_goal_from_message(
    session: AsyncSession,
    person_id: uuid.UUID,
    text: str,
    *,
    llm_goal: Any | None = None,
    event_id: uuid.UUID | None = None,
) -> bool:
    hit = resolve_goal_hit(text, llm_goal)
    if hit is None:
        return False
    return await apply_goal_hit(session, person_id, hit, event_id=event_id)


async def record_user_message(
    session: AsyncSession,
    person_id: uuid.UUID,
    content: str,
    *,
    source_id: uuid.UUID | None = None,
) -> None:
    append_event(
        session,
        person_id,
        kind="chat.user",
        summary=content,
        source_type="chat",
        source_id=source_id,
    )


def record_assistant_message(
    session: AsyncSession,
    person_id: uuid.UUID,
    content: str,
    *,
    source_id: uuid.UUID | None = None,
) -> None:
    append_event(
        session,
        person_id,
        kind="chat.assistant",
        summary=content,
        source_type="chat",
        source_id=source_id,
    )


async def record_onboarding(
    session: AsyncSession,
    person_id: uuid.UUID,
    *,
    intent: str | None,
) -> None:
    event = append_event(
        session,
        person_id,
        kind="onboarding.completed",
        summary="Onboarding completed",
        source_type="onboarding",
    )
    cleaned = (intent or "").strip()
    if not cleaned:
        return
    await apply_goal_hit(
        session,
        person_id,
        GoalHit(
            object_key=_GOAL_NOW,
            object_label=cleaned[:240],
            stance="pursuing",
            reason=None,
            evidence="onboarding",
        ),
        event_id=event.id,
    )


def record_vault_applied(
    session: AsyncSession,
    person_id: uuid.UUID,
    field_keys: list[str],
) -> None:
    if not field_keys:
        return
    keys = field_keys[:12]
    append_event(
        session,
        person_id,
        kind="vault.applied",
        summary="Vault updated: " + ", ".join(keys),
        source_type="vault",
        payload={"fieldKeys": keys},
    )


def record_document_processed(
    session: AsyncSession,
    person_id: uuid.UUID,
    *,
    document_id: uuid.UUID,
    filename: str,
) -> None:
    append_event(
        session,
        person_id,
        kind="document.processed",
        summary=f"Document processed: {filename}"[:_SUMMARY_MAX],
        source_type="document",
        source_id=document_id,
    )


async def list_goal_versions(
    session: AsyncSession, person_id: uuid.UUID, *, limit: int = 6
) -> list[PersonDecision]:
    result = await session.execute(
        select(PersonDecision)
        .where(
            PersonDecision.person_id == person_id,
            PersonDecision.object_key == _GOAL_NOW,
        )
        .order_by(PersonDecision.version.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_recent_events(
    session: AsyncSession, person_id: uuid.UUID, *, limit: int = 20
) -> list[PersonEvent]:
    result = await session.execute(
        select(PersonEvent)
        .where(PersonEvent.person_id == person_id)
        .order_by(PersonEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def goal_fact_lines(session: AsyncSession, person_id: uuid.UUID) -> list[str]:
    rows = await list_goal_versions(session, person_id, limit=2)
    if not rows:
        return []
    current = next((row for row in rows if row.status == _ACTIVE), None)
    previous = next((row for row in rows if row.status == _SUPERSEDED), None)
    lines: list[str] = []
    if current is not None:
        lines.append(f"Current goal ({current.stance}): {current.object_label}")
    if previous is not None:
        lines.append(
            f"Previous goal: {previous.object_label} — do not keep executing this plan"
        )
    return lines


def goal_to_public(row: PersonDecision) -> dict[str, Any]:
    return {
        "intent": row.object_label,
        "mode": row.stance,
        "reason": row.reason,
        "version": row.version,
        "evidence": row.evidence,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def event_to_public(row: PersonEvent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "kind": row.kind,
        "summary": row.summary,
        "sourceType": row.source_type,
        "occurredAt": row.occurred_at.isoformat() if row.occurred_at else None,
    }
