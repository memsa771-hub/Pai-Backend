"""Seed a small Person profile. Chat, documents, and later updates enrich the Vault."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.core.errors import AuthError, ValidationFailedError
from pai.onboarding.enums import (
    GOAL_TYPE_FOR_PRIMARY,
    PRIMARY_GOAL_TITLES,
    PrimaryGoal,
    field_enum_catalog,
)
from pai.onboarding.schema import (
    CONDITIONAL_FIELDS,
    ONBOARDING_PURPOSE,
    OPTIONAL_FIELDS,
    PATH_CHOICES,
    REQUIRED_FIELDS,
    OnboardingSubmit,
)
from pai.person.models import Education, Goal, Person, Skill, WorkExperience
from pai.vault.catalog import CATALOG_VERSION, get_catalog_field
from pai.vault.completion import apply_completion_to_vault
from pai.vault.service import VaultService

CV_AUTO_APPLY_CONFIDENCE = 0.8

_REQUIRED_LABELS = {
    "phone": "phone number",
    "dateOfBirth": "date of birth",
    "nationality": "nationality",
    "currentCountry": "current country",
    "currentCity": "current city",
    "currentStatus": "current status",
    "educationLevel": "education level",
    "gender": "gender",
    "primaryGoal": "primary goal",
}


def _sparse_get(sparse: dict[str, Any], key: str) -> Any:
    entry = sparse.get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def onboarding_public_status(
    person: Person | None, settings: Settings | None = None
) -> dict[str, Any]:
    resolved = settings or get_settings()
    completed = person is not None and person.onboarding_completed_at is not None
    payload: dict[str, Any] = {
        "onboardingCompleted": completed,
        "onboardingPath": getattr(person, "onboarding_path", None) if person else None,
        "nextPath": resolved.next_path(onboarding_completed=completed),
    }
    if completed and person is not None and person.onboarding_completed_at is not None:
        payload["onboardingCompletedAt"] = person.onboarding_completed_at.isoformat()
    return payload


class OnboardingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._vault = VaultService(self._settings)

    async def status(self, session: AsyncSession, person: Person) -> dict[str, Any]:
        self._require_vault(person)
        unified = await self._vault.get_unified_vault(session, person, include_sensitive=True)
        sparse = unified.get("sparseFields") or {}
        education = await self._first_education(session, person)
        goal = await self._first_goal(session, person)
        values = self._current_values(person, sparse, education, goal)
        missing = self._missing_required(values)
        completed = person.onboarding_completed_at is not None
        extracted = (
            await self._cv_candidates(session, person) if person.onboarding_path == "cv" else []
        )
        public = onboarding_public_status(person, self._settings)
        return {
            **public,
            "completed": completed,
            "completedAt": public.get("onboardingCompletedAt"),
            "path": person.onboarding_path,
            "choices": PATH_CHOICES if not completed and not person.onboarding_path else [],
            "purpose": ONBOARDING_PURPOSE,
            "vaultEnrichment": "chat_and_documents",
            "canComplete": not completed and not missing,
            "missingRequired": [] if completed else missing,
            "requiredFields": REQUIRED_FIELDS,
            "conditionalFields": CONDITIONAL_FIELDS,
            "optionalFields": OPTIONAL_FIELDS,
            "enums": field_enum_catalog(),
            "identity": {
                "fullName": person.full_name,
                "email": person.email,
                "phone": person.phone,
            },
            "values": values,
            "extractedFacts": extracted,
        }

    async def submit(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> dict[str, Any]:
        """Map the starting profile into the Vault and mark onboarding complete. Idempotent."""
        self._require_vault(person)
        person.onboarding_path = body.path or person.onboarding_path or "manual"
        await self._apply_submit(session, person, body)
        await self._touch_vault(session, person)
        await session.flush()
        unified = await self._vault.get_unified_vault(session, person, include_sensitive=True)
        sparse = unified.get("sparseFields") or {}
        education = await self._first_education(session, person)
        goal = await self._first_goal(session, person)
        values = self._current_values(person, sparse, education, goal)
        missing = self._missing_required(values)
        if missing:
            await session.rollback()
            labels = [_REQUIRED_LABELS.get(name, name) for name in missing]
            raise ValidationFailedError(
                "Onboarding is incomplete. Still needed: " + ", ".join(labels) + "."
            )
        if person.onboarding_completed_at is None:
            person.onboarding_completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(person)
        return await self.status(session, person)

    async def ingest_cv(
        self,
        session: AsyncSession,
        person: Person,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        storage: Any,
        gateway: Any,
    ) -> dict[str, Any]:
        """Extract CV facts into the vault. Never marks onboarding complete."""
        self._require_vault(person)
        person.onboarding_path = "cv"
        from pai.documents.models import DocumentCandidate, DocumentJob
        from pai.documents.service import create_document_upload, process_document_job
        from pai.ingestion.vault_apply import process_candidates
        from pai.orchestration.schemas import VaultCandidate

        doc = await create_document_upload(
            session,
            self._settings,
            person,
            filename=filename,
            content_type=content_type,
            data=data,
            storage=storage,
        )
        doc.document_type = "resume"
        await session.commit()
        result = await session.execute(
            select(DocumentJob)
            .where(DocumentJob.document_id == doc.id)
            .order_by(DocumentJob.created_at.desc())
        )
        job = result.scalars().first()
        if job is not None:
            try:
                await process_document_job(
                    session, self._settings, job, storage=storage, gateway=gateway
                )
                await session.commit()
            except Exception:
                job.status = "failed"
                await session.commit()
        pending = await session.execute(
            select(DocumentCandidate).where(
                DocumentCandidate.document_id == doc.id,
                DocumentCandidate.review_status == "pending",
            )
        )
        to_apply: list[VaultCandidate] = []
        for row in pending.scalars():
            if (row.confidence or 0) < CV_AUTO_APPLY_CONFIDENCE:
                continue
            row.review_status = "accepted"
            to_apply.append(
                VaultCandidate(
                    field_key=row.field_key,
                    value=row.value,
                    confidence=row.confidence,
                    evidence_text=row.evidence_text or "",
                    source_type="document",
                    source_reference=str(doc.id),
                    rationale_summary=row.reasoning_summary or "",
                )
            )
        if to_apply:
            await process_candidates(session, person, to_apply, from_document=True)
            await session.commit()
        await session.refresh(person)
        return await self.status(session, person)

    def _require_vault(self, person: Person) -> None:
        if person.vault is None:
            raise AuthError(
                code="VAULT_NOT_READY",
                message="Person vault not initialized. Call POST /api/v1/person/bootstrap.",
                status_code=400,
            )

    async def _touch_vault(self, session: AsyncSession, person: Person) -> None:
        if person.vault:
            person.vault.catalog_version = CATALOG_VERSION
            await apply_completion_to_vault(session, person, person.vault)

    async def _apply_submit(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        person.phone = body.phone
        await self._vault.ensure_consent(session, person.id, "demographics")
        await self._upsert_vault(
            session,
            person,
            "demographics.date_of_birth",
            body.dateOfBirth.isoformat(),
            skip_consent=True,
        )
        await self._upsert_vault(
            session, person, "demographics.nationality", body.nationality
        )
        await self._upsert_vault(
            session, person, "location.current_country", body.currentCountry
        )
        await self._upsert_vault(session, person, "location.current_city", body.currentCity)
        await self._upsert_vault(
            session, person, "identity.current_status", body.currentStatus.value
        )
        await self._upsert_vault(session, person, "demographics.gender", body.gender.value)
        if body.linkedinUrl:
            await self._upsert_vault(session, person, "social.linkedin_url", body.linkedinUrl)

        await self._upsert_vault(
            session, person, "education.highest_level", body.educationLevel.value
        )
        await self._upsert_education(session, person, body)
        await self._upsert_goal(session, person, body)

        destinations = list(body.targetCountries)
        if body.studyCountry and body.studyCountry not in destinations:
            destinations.insert(0, body.studyCountry)
        if destinations:
            await self._upsert_vault(
                session, person, "application.study_country", destinations[0]
            )
            if len(destinations) > 1:
                await self._upsert_vault(
                    session, person, "mobility.preferred_regions", destinations
                )
        if body.intake:
            cycle = body.intake.value
            if body.intakeYear:
                cycle = f"{cycle} {body.intakeYear}"
            await self._upsert_vault(session, person, "application.admission_cycle", cycle)
        if body.budget:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._upsert_vault(
                session, person, "finance.funding_status", body.budget.value, skip_consent=True
            )
        if body.scholarships is not None:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._upsert_vault(
                session,
                person,
                "finance.scholarship_interest",
                body.scholarships,
                skip_consent=True,
            )
        await self._upsert_skills(session, person, body)
        await self._upsert_work(session, person, body)

    async def _upsert_vault(
        self,
        session: AsyncSession,
        person: Person,
        field_key: str,
        value: Any,
        *,
        skip_consent: bool = False,
    ) -> None:
        field = get_catalog_field(field_key)
        if (
            field is None
            or field.derived
            or not field.editable
            or field.storage != "vault_value"
        ):
            return
        await self._vault.upsert_sparse_field(
            session,
            person,
            field_key,
            value,
            skip_consent_check=skip_consent or not field.consent_category,
        )

    async def _upsert_education(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        if not (
            body.institution
            or body.degree
            or body.major
            or body.gpa is not None
            or body.graduationYear is not None
        ):
            return
        degree = body.resolved_degree()
        row = await self._first_education(session, person)
        if row is None:
            if not body.institution:
                return
            session.add(
                Education(
                    person_id=person.id,
                    institution=body.institution,
                    degree=degree,
                    major=body.major.value if body.major else None,
                    gpa=body.gpa,
                    graduation_year=body.graduationYear,
                    status="completed",
                )
            )
        else:
            if body.institution:
                row.institution = body.institution
            if degree:
                row.degree = degree
            if body.major is not None:
                row.major = body.major.value
            if body.gpa is not None:
                row.gpa = body.gpa
            if body.graduationYear is not None:
                row.graduation_year = body.graduationYear
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "education" not in scopes:
                person.vault.applicable_scopes = scopes + ["education"]

    async def _upsert_goal(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        goal_key = body.primaryGoal.value
        title = (body.goalDetail or PRIMARY_GOAL_TITLES[goal_key])[:256]
        goal_type = GOAL_TYPE_FOR_PRIMARY[goal_key]
        row = await self._first_goal(session, person)
        if row is None:
            session.add(
                Goal(
                    person_id=person.id,
                    goal_type=goal_type,
                    title=title,
                    description=goal_key,
                    status="active",
                )
            )
        else:
            row.title = title
            row.goal_type = goal_type
            row.description = goal_key
            row.status = "active"
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "application" not in scopes:
                person.vault.applicable_scopes = scopes + ["application"]

    async def _upsert_skills(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        if not body.skills:
            return
        existing = await session.execute(select(Skill).where(Skill.person_id == person.id))
        known = {row.name.strip().lower() for row in existing.scalars() if row.name}
        for item in body.skills:
            key = item.name.strip().lower()
            if key in known:
                continue
            known.add(key)
            session.add(
                Skill(
                    person_id=person.id,
                    name=item.name.strip(),
                    proficiency=item.proficiency.value if item.proficiency else None,
                )
            )
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "career" not in scopes:
                person.vault.applicable_scopes = scopes + ["career"]

    async def _upsert_work(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        if not body.workExperience:
            return
        existing = await session.execute(
            select(WorkExperience).where(WorkExperience.person_id == person.id)
        )
        known = {
            (row.organization.strip().lower(), row.title.strip().lower())
            for row in existing.scalars()
            if row.organization and row.title
        }
        for item in body.workExperience:
            key = (item.organization.strip().lower(), item.title.strip().lower())
            if key in known:
                continue
            known.add(key)
            session.add(
                WorkExperience(
                    person_id=person.id,
                    organization=item.organization.strip(),
                    title=item.title.strip(),
                    employment_type=item.employmentType.value if item.employmentType else None,
                    is_current=item.isCurrent,
                    description=item.description,
                )
            )
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "career" not in scopes:
                person.vault.applicable_scopes = scopes + ["career"]

    def _current_values(
        self,
        person: Person,
        sparse: dict[str, Any],
        education: Education | None,
        goal: Goal | None,
    ) -> dict[str, Any]:
        return {
            "phone": person.phone,
            "dateOfBirth": _sparse_get(sparse, "demographics.date_of_birth"),
            "nationality": _sparse_get(sparse, "demographics.nationality"),
            "currentCountry": _sparse_get(sparse, "location.current_country"),
            "currentCity": _sparse_get(sparse, "location.current_city"),
            "currentStatus": _sparse_get(sparse, "identity.current_status"),
            "gender": _sparse_get(sparse, "demographics.gender"),
            "linkedinUrl": _sparse_get(sparse, "social.linkedin_url"),
            "educationLevel": _sparse_get(sparse, "education.highest_level"),
            "institution": education.institution if education else None,
            "degree": education.degree if education else None,
            "major": education.major if education else None,
            "gpa": education.gpa if education else None,
            "graduationYear": education.graduation_year if education else None,
            "primaryGoal": (
                goal.description
                if goal and goal.description in {item.value for item in PrimaryGoal}
                else None
            ),
            "goalDetail": goal.title if goal else None,
            "studyCountry": _sparse_get(sparse, "application.study_country"),
            "intake": _sparse_get(sparse, "application.admission_cycle"),
            "budget": _sparse_get(sparse, "finance.funding_status"),
            "scholarships": _sparse_get(sparse, "finance.scholarship_interest"),
        }

    def _missing_required(self, values: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for name in REQUIRED_FIELDS:
            if not _present(values.get(name)):
                missing.append(name)
        return missing

    async def _first_education(
        self, session: AsyncSession, person: Person
    ) -> Education | None:
        result = await session.execute(
            select(Education)
            .where(Education.person_id == person.id)
            .order_by(Education.created_at.asc())
        )
        return result.scalars().first()

    async def _first_goal(self, session: AsyncSession, person: Person) -> Goal | None:
        result = await session.execute(
            select(Goal)
            .where(Goal.person_id == person.id)
            .order_by(Goal.created_at.asc())
        )
        return result.scalars().first()

    async def _cv_candidates(self, session: AsyncSession, person: Person) -> list[dict[str, Any]]:
        from pai.documents.models import DocumentCandidate

        result = await session.execute(
            select(DocumentCandidate)
            .where(DocumentCandidate.person_id == person.id)
            .order_by(DocumentCandidate.created_at.desc())
        )
        out = []
        for row in result.scalars():
            out.append(
                {
                    "id": str(row.id),
                    "fieldKey": row.field_key,
                    "value": row.value,
                    "confidence": row.confidence,
                    "reviewStatus": row.review_status,
                    "evidence": row.evidence_text,
                }
            )
        return out[:40]
