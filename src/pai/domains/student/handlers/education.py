from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.education.resolver import ResolutionOutcome, resolve_education
from pai.domains.student.education.timeline import TIMELINE_ISSUE_TYPES, validate_education_timeline
from pai.domains.student.evidence import DEFAULT_VERIFICATION, attribute_verification, record_entity_evidence, verification_rank
from pai.domains.student.issues.service import DetectedIssue, record_issue, sync_issues
from pai.domains.student.person.models import Education, Person
from pai.domains.student.person.typed_resources import SCOPE_BY_RESOURCE
from pai.domains.student.vault.catalog import CatalogField
from pai.domains.student.vault.completion import apply_completion_to_vault
from pai.domains.student.vault.service import expand_scope_for_person
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import TypedApplyResult, _log_typed_history
EDUCATION_ENTITY = "education"
_MARKS_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
_GUARDED_EDUCATION_ATTRS = (
    "institution",
    "degree",
    "major",
    "gpa",
    "percentage",
    "graduation_year",
)

_CONTRADICTION_TYPE = {
    "gpa": "contradicting_grade",
    "percentage": "contradicting_grade",
    "graduation_year": "contradicting_date",
    "institution": "contradicting_institution",
}



def _education_payload(value: Any) -> dict[str, Any] | None:
    """Normalize education candidate values; never invent institution names."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        from pai.domains.student.person.qualifications import qualification_metadata
        return {"degree": text, "qualification_data": qualification_metadata({}, degree=text)}

    if not isinstance(value, dict):
        return None

    out: dict[str, Any] = {"qualification_data": dict(value)}
    if value.get("id"):
        out["id"] = str(value["id"])
    institution = value.get("institution")
    degree = value.get("degree") or value.get("program") or value.get("qualification")
    major = value.get("major") or value.get("stream") or value.get("group")
    from pai.domains.student.person.qualifications import qualification_metadata
    out["qualification_data"] = qualification_metadata(value, degree=degree, field=major)

    if institution and str(institution).strip():
        out["institution"] = str(institution).strip()
    if degree is not None and str(degree).strip():
        out["degree"] = str(degree).strip()
    if major is not None and str(major).strip():
        out["major"] = str(major).strip()

    from pai.domains.student.normalization.grades import finite_number
    if value.get("gpa") is not None:
        number = finite_number(value["gpa"])
        if number is None:
            return None
        out["gpa"] = number
    elif value.get("value") is not None and not institution:
        try:
            out["gpa"] = float(value["value"])
        except (TypeError, ValueError):
            pass
    if value.get("gpa_scale") is not None:
        out["gpa_scale"] = float(value["gpa_scale"])
    elif value.get("scale") is not None and "gpa" in out and not institution:
        try:
            out["gpa_scale"] = float(value["scale"])
        except (TypeError, ValueError):
            pass
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
    return out


async def _load_educations(session: AsyncSession, person_id: uuid.UUID) -> list[Education]:
    result = await session.execute(
        select(Education)
        .where(Education.person_id == person_id)
        .order_by(Education.updated_at.desc())
    )
    return list(result.scalars().all())


def _apply_qualification_identity(row: Education, payload: dict[str, Any]) -> None:
    """Store only explicit, evidence-backed qualification metadata."""
    if not row.original_name and payload.get("degree"):
        row.original_name = str(payload["degree"])[:256]
    metadata = payload.get("qualification_data") or {}
    level = metadata.get("canonicalLevel") or metadata.get("canonical_level")
    if level in {"secondary", "higher_secondary", "bachelor", "master", "phd"}:
        row.canonical_level = level
    if metadata.get("framework") and not row.framework:
        row.framework = str(metadata["framework"])
    if metadata.get("country") and not row.country:
        row.country = str(metadata["country"])
    row.qualification_data = {**(row.qualification_data or {}), **metadata}


def _contradiction_issue(
    row: Education,
    attribute: str,
    existing_value: Any,
    new_value: Any,
    existing_level: str,
    new_level: str,
) -> DetectedIssue:
    issue_type = _CONTRADICTION_TYPE.get(attribute, "contradicting_value")
    label = attribute.replace("_", " ")
    return DetectedIssue(
        domain="education",
        issue_type=issue_type,
        fingerprint=f"education:{issue_type}:{row.id}:{attribute}",
        severity="high" if attribute in ("gpa", "percentage") else "medium",
        confidence=0.8,
        related_entity_type="education",
        related_entity_ids=[str(row.id)],
        detail={
            "attribute": attribute,
            "existing": existing_value,
            "existingVerification": existing_level,
            "claimed": new_value,
            "claimedVerification": new_level,
            "institution": row.institution,
        },
        clarification_needed=True,
        clarification_prompt=(
            f"their {label} for {row.institution} is on file as {existing_value} "
            f"({existing_level.replace('_', ' ')}) but was just given as {new_value} — "
            "ask which is correct rather than overwriting"
        ),
    )


async def _apply_education_fields(
    session: AsyncSession,
    row: Education,
    payload: dict[str, Any],
    candidate: VaultCandidate,
    *,
    verification_level: str,
) -> tuple[list[str], list[DetectedIssue]]:
    """Write observed attributes, deferring to stronger existing evidence.

    A conflicting claim is never silently dropped or silently applied: the
    weaker one loses the write and is recorded as a contradiction so it can be
    asked about (doc §13).
    """
    strongest = await attribute_verification(
        session, EDUCATION_ENTITY, row.id, list(_GUARDED_EDUCATION_ATTRS)
    )
    written: list[str] = []
    conflicts: list[DetectedIssue] = []

    for attribute in ("institution", "degree", "major", "gpa", "percentage", "graduation_year"):
        if payload.get(attribute) is None:
            continue
        new_value = payload[attribute]
        current = getattr(row, attribute)
        if current == new_value:
            continue
        if current not in (None, ""):
            existing_level = strongest.get(attribute, DEFAULT_VERIFICATION)
            stronger_or_equal = verification_rank(verification_level) >= verification_rank(
                existing_level
            )
            if not (candidate.is_correction or stronger_or_equal):
                conflicts.append(
                    _contradiction_issue(
                        row, attribute, current, new_value, existing_level, verification_level
                    )
                )
                continue
        setattr(row, attribute, new_value)
        written.append(attribute)

    # Unguarded attributes: no prior claim to contradict.
    if payload.get("gpa_scale") is not None and row.gpa_scale != payload["gpa_scale"]:
        row.gpa_scale = payload["gpa_scale"]
        written.append("gpa_scale")
    if payload.get("status") and row.status != payload["status"]:
        row.status = payload["status"]
        written.append("status")

    _apply_qualification_identity(row, payload)
    for attribute in written:
        record_entity_evidence(
            session,
            entity_type=EDUCATION_ENTITY,
            entity_id=row.id,
            attribute=attribute,
            candidate=candidate,
            verification_level=verification_level,
        )
    return written, conflicts


def _education_snapshot(row: Education) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "institution": row.institution,
        "degree": row.degree,
        "major": row.major,
        "canonicalLevel": row.canonical_level,
        "qualificationData": row.qualification_data,
        "gpa": row.gpa,
        "percentage": row.percentage,
        "graduation_year": row.graduation_year,
    }


async def _ambiguity_issue(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    outcome: ResolutionOutcome,
    payload: dict[str, Any],
) -> None:
    """Record that an observation could describe more than one record (doc §10)."""
    rival_ids = sorted(str(row.id) for row in outcome.rivals)
    fingerprint_parts = rival_ids or [candidate.field_key]
    described = ", ".join(
        str(payload.get(key)) for key in ("gpa", "percentage", "degree") if payload.get(key)
    )
    await record_issue(
        session,
        person.id,
        DetectedIssue(
            domain="education",
            issue_type="ambiguous_entity",
            fingerprint="education:ambiguous_entity:" + ":".join(fingerprint_parts),
            severity="medium",
            confidence=0.75,
            related_entity_type="education",
            related_entity_ids=rival_ids,
            detail={
                "observation": {k: v for k, v in payload.items() if not k.startswith("_")},
                "reason": outcome.reason,
                "evidenceText": candidate.evidence_text,
            },
            clarification_needed=True,
            clarification_prompt=(
                f"they mentioned {described or 'an academic detail'} but it could belong to "
                "more than one of their qualifications — ask which one it refers to"
            ),
        ),
        detected_from=f"{candidate.source_type}:education_write",
    )


async def revalidate_education_timeline(
    session: AsyncSession,
    person: Person,
    *,
    detected_from: str,
) -> None:
    """Re-derive timeline issues from the student's full education history."""
    rows = await _load_educations(session, person.id)
    await sync_issues(
        session,
        person.id,
        validate_education_timeline(rows),
        domain="education",
        authoritative_types=TIMELINE_ISSUE_TYPES,
        detected_from=detected_from,
    )


async def _apply_education_one(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    field: CatalogField,
    *,
    vault_status: str,
    recompute_completion: bool,
    verification_level: str = DEFAULT_VERIFICATION,
    validate_timeline: bool = True,
) -> TypedApplyResult:
    payload = _education_payload(candidate.value)
    if payload is None and field.key in ("education.gpa", "education.program"):
        # A bare grade with no qualification named. The resolver decides whether
        # the student has exactly one record it could belong to.
        if isinstance(candidate.value, (int, float)):
            payload = {"gpa": float(candidate.value)}
        elif isinstance(candidate.value, str) and _MARKS_RE.match(candidate.value):
            m = _MARKS_RE.match(candidate.value)
            assert m
            obtained, total = float(m.group(1)), float(m.group(2))
            payload = {"percentage": round(100.0 * obtained / total, 2)} if total else None

    if payload is None:
        return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)

    institution = (payload.get("institution") or "").strip()
    invented = bool(institution) and institution in (payload.get("degree"), payload.get("major"))

    rows = await _load_educations(session, person.id)
    outcome = resolve_education(payload, rows)
    if outcome.ambiguous:
        await _ambiguity_issue(session, person, candidate, outcome, payload)
        return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)

    existing = outcome.match
    old_snapshot = _education_snapshot(existing) if existing else None
    conflicts: list[DetectedIssue] = []
    if existing is not None:
        if invented:
            payload = {k: v for k, v in payload.items() if k != "institution"}
        _written, conflicts = await _apply_education_fields(
            session, existing, payload, candidate, verification_level=verification_level
        )
        row = existing
        status = "updated"
    elif invented or not (institution or payload.get("degree")):
        return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
    else:
        row = Education(
            person_id=person.id,
            institution=payload.get("institution"),
            degree=payload.get("degree"),
            major=payload.get("major"),
            gpa=payload.get("gpa"),
            gpa_scale=payload.get("gpa_scale"),
            percentage=payload.get("percentage"),
            graduation_year=payload.get("graduation_year"),
            status=payload.get("status") or "completed",
            qualification_data=payload.get("qualification_data"),
        )
        _apply_qualification_identity(row, payload)
        session.add(row)
        await session.flush()
        for attribute in ("institution", "degree", "major", "gpa", "percentage", "graduation_year"):
            if payload.get(attribute) is not None:
                record_entity_evidence(
                    session,
                    entity_type=EDUCATION_ENTITY,
                    entity_id=row.id,
                    attribute=attribute,
                    candidate=candidate,
                    verification_level=verification_level,
                )
        status = "accepted"

    for conflict in conflicts:
        await record_issue(
            session,
            person.id,
            conflict,
            detected_from=f"{candidate.source_type}:education_write",
        )

    await expand_scope_for_person(session, person, SCOPE_BY_RESOURCE["educations"])
    await _log_typed_history(
        session,
        person,
        candidate.field_key,
        old_value=old_snapshot,
        new_value=_education_snapshot(row),
        candidate=candidate,
        entity_type=EDUCATION_ENTITY,
        entity_id=row.id,
    )
    if validate_timeline:
        await revalidate_education_timeline(
            session, person, detected_from=f"{candidate.source_type}:education_write"
        )
    if recompute_completion and person.vault:
        await apply_completion_to_vault(session, person, person.vault)
    out = "pending" if vault_status == "pending" else status
    return TypedApplyResult(candidate.field_key, out, candidate.confidence)



from pai.domains.student.handlers.common import _as_items

async def apply(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    field: CatalogField,
    *,
    vault_status: str,
    recompute_completion: bool = True,
    verification_level: str = DEFAULT_VERIFICATION,
) -> TypedApplyResult:
    if vault_status == "pending":
        from pai.kernel.evidence.vault_apply import apply_vault_candidate
        result = await apply_vault_candidate(
            session, person, candidate, vault_status="pending",
            verification_level=verification_level,
            recompute_completion=recompute_completion,
        )
        return TypedApplyResult(result.field_key, result.status, result.confidence)
    items = _as_items(candidate.value) if isinstance(candidate.value, list) else None
    if items:
        last = TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
        for item in items:
            piece = candidate.model_copy(update={"value": item})
            last = await _apply_education_one(
                session,
                person,
                piece,
                field,
                vault_status=vault_status,
                recompute_completion=False,
                verification_level=verification_level,
                validate_timeline=False,
            )
        # One validation pass over the finished timeline, not one per row.
        await revalidate_education_timeline(
            session, person, detected_from=f"{candidate.source_type}:education_write"
        )
        if recompute_completion and person.vault:
            await apply_completion_to_vault(session, person, person.vault)
        return last
    return await _apply_education_one(
        session,
        person,
        candidate,
        field,
        vault_status=vault_status,
        recompute_completion=recompute_completion,
        verification_level=verification_level,
    )

