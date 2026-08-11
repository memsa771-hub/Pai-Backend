from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.orchestration.schemas import VaultCandidate
from auth_service.person.models import Education, Goal, Person, VaultHistory
from auth_service.person.typed_resources import SCOPE_BY_RESOURCE
from auth_service.vault.service import expand_scope_for_person
from auth_service.vault.catalog import CatalogField, get_catalog_field
from auth_service.vault.completion import apply_completion_to_vault


class TypedApplyResult:
    __slots__ = ("field_key", "status", "confidence")

    def __init__(self, field_key: str, status: str, confidence: float) -> None:
        self.field_key = field_key
        self.status = status
        self.confidence = confidence


def _education_payload(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        institution = value.get("institution")
        if not institution or not str(institution).strip():
            return None
        out: dict[str, Any] = {"institution": str(institution).strip()}
        if value.get("degree") is not None:
            out["degree"] = str(value["degree"])
        if value.get("major") is not None:
            out["major"] = str(value["major"])
        if value.get("gpa") is not None:
            out["gpa"] = float(value["gpa"])
        return out
    return None


async def _find_education(
    session: AsyncSession, person_id: uuid.UUID, institution: str
) -> Education | None:
    result = await session.execute(
        select(Education).where(
            Education.person_id == person_id,
            Education.institution == institution,
        )
    )
    return result.scalar_one_or_none()


async def _log_typed_history(
    session: AsyncSession,
    person: Person,
    field_key: str,
    *,
    old_value: Any,
    new_value: Any,
    candidate: VaultCandidate,
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
            reason=(
                f"{candidate.source_type}:{candidate.source_reference}:"
                f"{(candidate.rationale_summary or '')[:180]}"
            ),
        )
    )


async def apply_typed_candidate(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    field: CatalogField,
    *,
    vault_status: str,
) -> TypedApplyResult:
    if field.storage == "educations":
        payload = _education_payload(candidate.value)
        if payload is None and field.key == "education.gpa":
            if isinstance(candidate.value, (int, float)):
                payload = {"institution": "Primary education", "gpa": float(candidate.value)}
        if payload is None:
            return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
        institution = payload["institution"]
        existing = await _find_education(session, person.id, institution)
        old_snapshot = None
        if existing:
            old_snapshot = {
                "id": str(existing.id),
                "institution": existing.institution,
                "degree": existing.degree,
                "gpa": existing.gpa,
            }
            if payload.get("degree"):
                existing.degree = payload["degree"]
            if payload.get("major"):
                existing.major = payload["major"]
            if payload.get("gpa") is not None:
                existing.gpa = payload["gpa"]
            row = existing
            status = "updated"
        else:
            row = Education(
                person_id=person.id,
                institution=institution,
                degree=payload.get("degree"),
                major=payload.get("major"),
                gpa=payload.get("gpa"),
            )
            session.add(row)
            await session.flush()
            status = "accepted"
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["educations"])
        new_snapshot = {
            "id": str(row.id),
            "institution": row.institution,
            "degree": row.degree,
            "gpa": row.gpa,
        }
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=old_snapshot,
            new_value=new_snapshot,
            candidate=candidate,
        )
        if person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else status
        return TypedApplyResult(candidate.field_key, out, candidate.confidence)

    if field.storage == "goals" and field.key == "application.career_interest":
        title = candidate.value if isinstance(candidate.value, str) else str(candidate.value)
        goal = Goal(
            person_id=person.id,
            title=title[:256],
            goal_type="career",
            status="active" if vault_status != "pending" else "proposed",
        )
        session.add(goal)
        await session.flush()
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["goals"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value={"id": str(goal.id), "title": goal.title},
            candidate=candidate,
        )
        if person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else "accepted"
        return TypedApplyResult(candidate.field_key, out, candidate.confidence)

    if field.storage == "person" and field.person_column:
        old = getattr(person, field.person_column, None)
        setattr(person, field.person_column, candidate.value)
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=old,
            new_value=candidate.value,
            candidate=candidate,
        )
        if person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else "accepted"
        return TypedApplyResult(candidate.field_key, out, candidate.confidence)

    return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
