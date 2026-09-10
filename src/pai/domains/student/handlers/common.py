from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Person, VaultHistory
from pai.kernel.contracts.schemas import VaultCandidate


class TypedApplyResult:
    __slots__ = ("field_key", "status", "confidence")

    def __init__(self, field_key: str, status: str, confidence: float) -> None:
        self.field_key = field_key
        self.status = status
        self.confidence = confidence


async def _log_typed_history(
    session: AsyncSession,
    person: Person,
    field_key: str,
    *,
    old_value: Any,
    new_value: Any,
    candidate: VaultCandidate,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> None:
    if person.vault is None:
        return
    session.add(
        VaultHistory(
            vault_id=person.vault.id,
            field_key=field_key,
            action="updated" if old_value is not None else "created",
            old_value=old_value,
            new_value=new_value,
            actor_type="system",
            actor_id=str(person.id),
            entity_type=entity_type,
            entity_id=entity_id,
            reason=(
                f"{candidate.source_type}:{candidate.source_reference}:"
                f"{(candidate.rationale_summary or '')[:180]}"
            ),
        )
    )


_MANUAL_TYPED = {
    "educations": (
        "education",
        "education.program",
        ("institution", "degree", "major", "gpa", "percentage", "graduation_year"),
    ),
    "work_experiences": ("work", "career.work_history", ("organization", "title")),
    "projects": ("project", "career.projects", ("name", "role")),
    "skills": ("skill", "career.skills", ("name", "proficiency")),
    "certifications": ("certification", "career.certifications", ("name", "issuer")),
}


def _typed_snapshot(row: Any, attributes: tuple[str, ...]) -> dict[str, Any]:
    return {
        name: getattr(row, name, None)
        for name in attributes
        if getattr(row, name, None) is not None
    }


async def audit_manual_typed_write(
    session: AsyncSession,
    person: Person,
    row: Any,
    *,
    old_value: Any = None,
) -> None:
    spec = _MANUAL_TYPED.get(getattr(row, "__tablename__", None))
    if spec is None or person.vault is None or getattr(row, "id", None) is None:
        return
    entity_type, field_key, attributes = spec
    snapshot = _typed_snapshot(row, attributes)
    if not snapshot:
        return
    from pai.domains.student.evidence import record_entity_evidence

    candidate = VaultCandidate(
        field_key=field_key,
        value=snapshot,
        confidence=1.0,
        source_type="manual",
        source_reference=str(person.id),
        evidence_text="",
        assertion_status="explicit",
    )
    for attribute in snapshot:
        record_entity_evidence(
            session,
            entity_type=entity_type,
            entity_id=row.id,
            attribute=attribute,
            candidate=candidate,
        )
    await _log_typed_history(
        session,
        person,
        field_key,
        old_value=old_value,
        new_value=snapshot,
        candidate=candidate,
        entity_type=entity_type,
        entity_id=row.id,
    )


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    return [value]


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


