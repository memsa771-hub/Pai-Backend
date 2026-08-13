from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.conversations.models import Conversation, Message
from pai.documents.models import Document
from pai.person.models import Person, VaultValue
from pai.person.profile_snapshot import load_typed_profile_records
from pai.vault.service import VaultService


class PersonContextPack(BaseModel):
    person_id: str
    identity: dict[str, Any] = Field(default_factory=dict)
    applicable_vault_fields: dict[str, Any] = Field(default_factory=dict)
    typed_profile_summary: dict[str, Any] = Field(default_factory=dict)
    vault_completion: dict[str, Any] = Field(default_factory=dict)
    missing_critical_fields: list[str] = Field(default_factory=list)
    # Explicit list the counselor must not re-ask
    known_facts: list[str] = Field(default_factory=list)
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    # Recent turns from OTHER threads (when clients fragment conversationIds)
    cross_thread_recent: list[dict[str, str]] = Field(default_factory=list)
    conversation_topic: str | None = None
    pending_conflicts: list[str] = Field(default_factory=list)
    relevant_documents: list[dict[str, str]] = Field(default_factory=list)
    active_tasks: list[dict[str, str]] = Field(default_factory=list)
    proposed_tasks: list[dict[str, str]] = Field(default_factory=list)
    applied_vault_changes_turn: list[dict[str, Any]] = Field(default_factory=list)


StudentContextPack = PersonContextPack


from pai.tasks.service import list_tasks_for_person


def _sparse_value(entry: Any) -> Any:
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def build_known_facts(
    *,
    identity: dict[str, Any],
    sparse: dict[str, Any],
    typed: dict[str, Any],
) -> list[str]:
    """Human-readable facts already known — counselor must not re-ask these."""
    facts: list[str] = []
    name = identity.get("preferredName") or identity.get("fullName")
    if name:
        facts.append(f"Student name: {name}")

    for edu in typed.get("educations") or []:
        parts = [
            p
            for p in (
                edu.get("degree"),
                edu.get("major"),
                edu.get("institution"),
            )
            if p
        ]
        detail = " / ".join(str(p) for p in parts) if parts else "education record"
        if edu.get("gpa") is not None:
            scale = edu.get("gpaScale") or 4.0
            detail += f", GPA/CGPA {edu['gpa']}/{scale}"
        if edu.get("percentage") is not None:
            detail += f", {edu['percentage']}%"
        facts.append(f"Education: {detail}")

    for goal in typed.get("goals") or []:
        if goal.get("title"):
            facts.append(f"Career/study goal: {goal['title']}")

    for skill in (typed.get("skills") or [])[:12]:
        if skill.get("name"):
            facts.append(f"Skill: {skill['name']}")

    for key, label in (
        ("application.study_country", "Target study country/countries"),
        ("application.career_interest", "Career interest"),
        ("application.target_universities", "Target universities"),
        ("application.admission_cycle", "Admission cycle"),
        ("mobility.preferred_regions", "Preferred regions"),
        ("education.stream", "Education stream"),
        ("education.marks", "Marks"),
        ("education.additional_maths", "Additional Maths"),
        ("location.current_city", "Current city"),
        ("location.current_country", "Current country"),
        ("demographics.gender", "Gender"),
        ("demographics.nationality", "Nationality"),
        ("demographics.date_of_birth", "Date of birth"),
        ("identity.current_status", "Current status"),
        ("social.linkedin_url", "LinkedIn"),
        ("education.highest_level", "Highest education level"),
        ("preferences.preferred_language", "Preferred language"),
        ("preferences.learning_style", "Learning style"),
        ("preferences.communication_style", "Communication style"),
        ("finance.funding_status", "Funding / budget status"),
        ("finance.scholarship_interest", "Scholarship interest"),
        ("mobility.relocation_willingness", "Relocation willingness"),
    ):
        if key in sparse:
            facts.append(f"{label}: {_sparse_value(sparse[key])}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for f in facts:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


async def _load_cross_thread_messages(
    session: AsyncSession,
    person_id: uuid.UUID,
    *,
    exclude_conversation_id: uuid.UUID | None,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Last N messages across all active threads (helps when clients split chats)."""
    q = (
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.person_id == person_id,
            Conversation.person_id == person_id,
            Conversation.status == "active",
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if exclude_conversation_id is not None:
        q = q.where(Message.conversation_id != exclude_conversation_id)
    result = await session.execute(q)
    rows = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in rows]


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
    sparse = unified.get("sparseFields") or {}
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
    cross = await _load_cross_thread_messages(
        session,
        person.id,
        exclude_conversation_id=conversation_id,
        limit=min(12, limit),
    )
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
    identity = {
        "email": person.email,
        "fullName": person.full_name,
        "preferredName": person.preferred_name,
    }
    known = build_known_facts(identity=identity, sparse=sparse, typed=typed_records)
    return PersonContextPack(
        person_id=str(person.id),
        identity=identity,
        applicable_vault_fields=sparse,
        typed_profile_summary=typed_records,
        vault_completion=completion,
        missing_critical_fields=list(completion.get("missingCriticalFields") or []),
        known_facts=known,
        recent_messages=recent,
        cross_thread_recent=cross,
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
