from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.config import Settings, get_settings
from auth_service.conversations.models import Conversation, Message
from auth_service.documents.models import Document
from auth_service.person.models import Person, VaultValue
from auth_service.person.profile_snapshot import load_typed_profile_records
from auth_service.vault.service import VaultService


class PersonContextPack(BaseModel):
    person_id: str
    identity: dict[str, Any] = Field(default_factory=dict)
    applicable_vault_fields: dict[str, Any] = Field(default_factory=dict)
    typed_profile_summary: dict[str, Any] = Field(default_factory=dict)
    vault_completion: dict[str, Any] = Field(default_factory=dict)
    missing_critical_fields: list[str] = Field(default_factory=list)
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    conversation_topic: str | None = None
    pending_conflicts: list[str] = Field(default_factory=list)
    relevant_documents: list[dict[str, str]] = Field(default_factory=list)
    active_tasks: list[dict[str, str]] = Field(default_factory=list)
    proposed_tasks: list[dict[str, str]] = Field(default_factory=list)
    applied_vault_changes_turn: list[dict[str, Any]] = Field(default_factory=list)


StudentContextPack = PersonContextPack


from auth_service.tasks.service import list_tasks_for_person


async def build_person_context_pack(
    session: AsyncSession,
    person: Person,
    *,
    conversation_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> PersonContextPack:
    settings = settings or get_settings()
    if person.vault is None:
        await session.refresh(person, attribute_names=["vault"])
    vault_svc = VaultService(settings)
    unified = await vault_svc.get_unified_vault(session, person, include_sensitive=False)
    completion = unified.get("completion") or {}
    limit = settings.chat_recent_message_limit
    recent: list[dict[str, str]] = []
    topic: str | None = None
    if conversation_id:
        conv = await session.get(Conversation, conversation_id)
        if conv is None or conv.person_id != person.id:
            conv = None
            topic = None
            recent = []
        else:
            topic = conv.topic
            result = await session.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.person_id == person.id,
                )
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            rows = list(reversed(result.scalars().all()))
            recent = [{"role": m.role, "content": m.content} for m in rows]
    docs = await session.execute(
        select(Document)
        .where(
            Document.person_id == person.id,
            Document.status.in_(["processed", "awaiting_review", "processing"]),
        )
        .limit(5)
    )
    doc_summaries = [
        {"id": str(d.id), "filename": d.original_filename, "type": d.document_type or "generic"}
        for d in docs.scalars()
    ]
    pending_conflicts: list[str] = []
    if person.vault is not None:
        pending_rows = await session.execute(
            select(VaultValue.field_key).where(
                VaultValue.vault_id == person.vault.id,
                VaultValue.status == "pending_confirmation",
            )
        )
        pending_conflicts = list(pending_rows.scalars().all())
    tasks = await list_tasks_for_person(session, person.id)
    active_tasks = [
        {"id": str(t.id), "title": t.title, "status": t.status} for t in tasks if t.status != "proposed"
    ]
    proposed_tasks = [
        {"id": str(t.id), "title": t.title, "status": t.status} for t in tasks if t.status == "proposed"
    ]
    typed_records = await load_typed_profile_records(session, person.id)
    return PersonContextPack(
        person_id=str(person.id),
        identity={
            "email": person.email,
            "fullName": person.full_name,
            "preferredName": person.preferred_name,
        },
        applicable_vault_fields=unified.get("sparseFields") or {},
        # Full typed rows (educations/goals/…) so counselor can avoid re-asking known facts.
        typed_profile_summary=typed_records,
        vault_completion=completion,
        missing_critical_fields=list(completion.get("missingCriticalFields") or []),
        recent_messages=recent,
        conversation_topic=topic,
        pending_conflicts=pending_conflicts,
        relevant_documents=doc_summaries,
        active_tasks=active_tasks,
        proposed_tasks=proposed_tasks,
    )


async def build_student_context_pack(
    session: AsyncSession,
    person: Person,
    *,
    conversation_id: uuid.UUID | None = None,
    settings: Settings | None = None,
    applied_vault_changes_turn: list[dict[str, Any]] | None = None,
) -> StudentContextPack:
    pack = await build_person_context_pack(
        session, person, conversation_id=conversation_id, settings=settings
    )
    if applied_vault_changes_turn:
        pack.applied_vault_changes_turn = applied_vault_changes_turn
    return pack


def context_pack_to_json(pack: PersonContextPack | StudentContextPack) -> str:
    return json.dumps(pack.model_dump(), default=str)
