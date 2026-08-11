from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.orchestration.schemas import VaultCandidate
from auth_service.person.models import Education, Goal, Person, VaultHistory
from auth_service.person.typed_resources import SCOPE_BY_RESOURCE
from auth_service.vault.catalog import CatalogField
from auth_service.vault.completion import apply_completion_to_vault
from auth_service.vault.service import expand_scope_for_person


class TypedApplyResult:
    __slots__ = ("field_key", "status", "confidence")

    def __init__(self, field_key: str, status: str, confidence: float) -> None:
        self.field_key = field_key
        self.status = status
        self.confidence = confidence


_MARKS_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")


def _education_payload(value: Any) -> dict[str, Any] | None:
    """Normalize education candidate values; never invent institution names."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # "FSc Pre-Medical" / "BS Computer Science"
        return {"degree": text, "institution": text}

    if not isinstance(value, dict):
        return None

    out: dict[str, Any] = {}
    institution = value.get("institution")
    degree = value.get("degree") or value.get("program") or value.get("qualification")
    major = value.get("major") or value.get("stream") or value.get("group")

    if institution and str(institution).strip():
        out["institution"] = str(institution).strip()
    if degree is not None and str(degree).strip():
        out["degree"] = str(degree).strip()
    if major is not None and str(major).strip():
        out["major"] = str(major).strip()

    if value.get("gpa") is not None:
        out["gpa"] = float(value["gpa"])
    if value.get("gpa_scale") is not None:
        out["gpa_scale"] = float(value["gpa_scale"])
    if value.get("graduation_year") is not None:
        out["graduation_year"] = int(value["graduation_year"])
    if value.get("status") is not None:
        out["status"] = str(value["status"])

    marks_obtained = value.get("marks_obtained") or value.get("obtained")
    marks_total = value.get("marks_total") or value.get("total")
    marks = value.get("marks")
    if marks is not None and marks_obtained is None:
        if isinstance(marks, str) and _MARKS_RE.match(marks):
            m = _MARKS_RE.match(marks)
            assert m
            marks_obtained, marks_total = float(m.group(1)), float(m.group(2))
        elif isinstance(marks, dict):
            marks_obtained = marks.get("obtained") or marks.get("marks_obtained")
            marks_total = marks.get("total") or marks.get("marks_total")

    if marks_obtained is not None and marks_total is not None:
        obtained = float(marks_obtained)
        total = float(marks_total)
        if total > 0:
            out["percentage"] = round(100.0 * obtained / total, 2)
            # Keep raw marks in status-free side channel via description fields on row
            out["_marks_obtained"] = obtained
            out["_marks_total"] = total
    elif value.get("percentage") is not None:
        out["percentage"] = float(value["percentage"])

    # Need at least one identifying academic signal
    if not any(k in out for k in ("institution", "degree", "major", "gpa", "percentage")):
        return None

    # Prefer a real label for institution; fall back to degree/major label (not "Primary education")
    if "institution" not in out:
        label = out.get("degree") or out.get("major")
        if label:
            out["institution"] = str(label)
        else:
            return None
    return out


async def _find_education_match(
    session: AsyncSession,
    person_id: uuid.UUID,
    payload: dict[str, Any],
) -> Education | None:
    institution = payload.get("institution")
    if institution:
        result = await session.execute(
            select(Education).where(
                Education.person_id == person_id,
                Education.institution == institution,
            )
        )
        hit = result.scalar_one_or_none()
        if hit:
            return hit

    degree = payload.get("degree")
    major = payload.get("major")
    if degree or major:
        result = await session.execute(
            select(Education)
            .where(Education.person_id == person_id)
            .order_by(Education.updated_at.desc())
        )
        for row in result.scalars().all():
            deg_ok = not degree or (row.degree or "").lower() == str(degree).lower()
            maj_ok = not major or (row.major or "").lower() == str(major).lower()
            inst_ok = not institution or (row.institution or "").lower() == str(institution).lower()
            if deg_ok and maj_ok and (inst_ok or not institution):
                if degree or major:
                    return row

    # Bare GPA/percentage correction against single/most-recent education
    if payload.get("gpa") is not None or payload.get("percentage") is not None:
        result = await session.execute(
            select(Education)
            .where(Education.person_id == person_id)
            .order_by(Education.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    return None


def _apply_education_fields(row: Education, payload: dict[str, Any]) -> None:
    if payload.get("institution") and row.institution != payload["institution"]:
        # Keep established institution unless it was a placeholder equal to degree
        if row.institution in (row.degree, row.major, None, ""):
            row.institution = payload["institution"]
    if payload.get("degree"):
        row.degree = payload["degree"]
    if payload.get("major"):
        row.major = payload["major"]
    if payload.get("gpa") is not None:
        row.gpa = payload["gpa"]
    if payload.get("gpa_scale") is not None:
        row.gpa_scale = payload["gpa_scale"]
    if payload.get("percentage") is not None:
        row.percentage = payload["percentage"]
    if payload.get("graduation_year") is not None:
        row.graduation_year = payload["graduation_year"]
    if payload.get("status"):
        row.status = payload["status"]


def _education_snapshot(row: Education) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "institution": row.institution,
        "degree": row.degree,
        "major": row.major,
        "gpa": row.gpa,
        "percentage": row.percentage,
        "graduation_year": row.graduation_year,
    }


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


async def _upsert_career_goal(
    session: AsyncSession,
    person: Person,
    title: str,
    *,
    vault_status: str,
) -> tuple[Goal, str, dict[str, Any] | None]:
    """Keep one canonical career goal; update instead of duplicating."""
    normalized = title.strip().lower()
    result = await session.execute(
        select(Goal)
        .where(Goal.person_id == person.id, Goal.goal_type == "career")
        .order_by(Goal.updated_at.desc())
    )
    rows = list(result.scalars().all())
    for row in rows:
        if row.title.strip().lower() == normalized:
            return row, "reinforced", _goal_snap(row)
        # Soft match: same program acronym inside title (BSCS / BS CS)
        if normalized in row.title.lower() or row.title.lower() in normalized:
            old = _goal_snap(row)
            row.title = title[:256]
            row.status = "active" if vault_status != "pending" else row.status
            return row, "updated", old

    if rows:
        # Single career objective: update the newest rather than spawn duplicates
        row = rows[0]
        old = _goal_snap(row)
        row.title = title[:256]
        row.status = "active" if vault_status != "pending" else "proposed"
        return row, "updated", old

    goal = Goal(
        person_id=person.id,
        title=title[:256],
        goal_type="career",
        status="active" if vault_status != "pending" else "proposed",
    )
    session.add(goal)
    await session.flush()
    return goal, "accepted", None


def _goal_snap(row: Goal) -> dict[str, Any]:
    return {"id": str(row.id), "title": row.title, "status": row.status}


async def apply_typed_candidate(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    field: CatalogField,
    *,
    vault_status: str,
    recompute_completion: bool = True,
) -> TypedApplyResult:
    if field.storage == "educations":
        payload = _education_payload(candidate.value)
        # Bare numeric GPA/percentage: merge into most recent education if one exists
        if payload is None and field.key in ("education.gpa", "education.program"):
            if isinstance(candidate.value, (int, float)):
                existing = await _find_education_match(
                    session, person.id, {"gpa": float(candidate.value)}
                )
                if existing is None:
                    return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
                payload = {"institution": existing.institution, "gpa": float(candidate.value)}
            elif isinstance(candidate.value, str) and _MARKS_RE.match(candidate.value):
                m = _MARKS_RE.match(candidate.value)
                assert m
                obtained, total = float(m.group(1)), float(m.group(2))
                pct = round(100.0 * obtained / total, 2) if total else None
                existing = await _find_education_match(
                    session, person.id, {"percentage": pct or 0}
                )
                if existing is None:
                    # Do not invent institutions for orphan mark strings.
                    return TypedApplyResult(
                        candidate.field_key, "rejected", candidate.confidence
                    )
                payload = {
                    "institution": existing.institution,
                    "percentage": pct,
                }

        if payload is None:
            return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)

        existing = await _find_education_match(session, person.id, payload)
        old_snapshot = _education_snapshot(existing) if existing else None
        if existing:
            _apply_education_fields(existing, payload)
            row = existing
            status = "updated"
        else:
            row = Education(
                person_id=person.id,
                institution=payload["institution"],
                degree=payload.get("degree"),
                major=payload.get("major"),
                gpa=payload.get("gpa"),
                gpa_scale=payload.get("gpa_scale"),
                percentage=payload.get("percentage"),
                graduation_year=payload.get("graduation_year"),
                status=payload.get("status") or "completed",
            )
            session.add(row)
            await session.flush()
            status = "accepted"
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["educations"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=old_snapshot,
            new_value=_education_snapshot(row),
            candidate=candidate,
        )
        if recompute_completion and person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else status
        return TypedApplyResult(candidate.field_key, out, candidate.confidence)

    if field.storage == "goals" and field.key == "application.career_interest":
        title = candidate.value if isinstance(candidate.value, str) else str(candidate.value)
        goal, status, old = await _upsert_career_goal(
            session, person, title, vault_status=vault_status
        )
        await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["goals"])
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=old,
            new_value=_goal_snap(goal),
            candidate=candidate,
        )
        if recompute_completion and person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else status
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
        if recompute_completion and person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        out = "pending" if vault_status == "pending" else "accepted"
        return TypedApplyResult(candidate.field_key, out, candidate.confidence)

    return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
