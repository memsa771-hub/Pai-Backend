"""Persist onboarding into Person + Person Vault (manual or CV)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.core.errors import AuthError, ValidationFailedError
from pai.onboarding.schema import (
    DEGREE_FOR_LEVEL,
    PATH_CHOICES,
    STEP_META,
    OnboardingGapAnswers,
    OnboardingPath,
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep3,
)
from pai.person.models import Education, Goal, Person
from pai.vault.catalog import CATALOG_VERSION
from pai.vault.completion import apply_completion_to_vault, load_presence_snapshot
from pai.vault.service import VaultService

TOTAL_STEPS = 3
CV_AUTO_APPLY_CONFIDENCE = 0.8


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
        snapshot = await load_presence_snapshot(session, person, person.vault)
        unified = await self._vault.get_unified_vault(session, person, include_sensitive=True)
        sparse = unified.get("sparseFields") or {}
        education = await self._first_education(session, person)
        goal = await self._first_goal(session, person)
        path = person.onboarding_path
        missing = self._missing_required(path, sparse, snapshot, education, goal)
        steps = [
            self._step_view(1, person, sparse, education, goal),
            self._step_view(2, person, sparse, education, goal),
            self._step_view(3, person, sparse, education, goal),
        ]
        current = next((s["step"] for s in steps if not s["complete"]), None)
        completed = person.onboarding_completed_at is not None
        extracted = await self._cv_candidates(session, person) if path == "cv" else []
        return {
            "completed": completed,
            "completedAt": (
                person.onboarding_completed_at.isoformat()
                if person.onboarding_completed_at
                else None
            ),
            "path": path,
            "choices": PATH_CHOICES if not path and not completed else [],
            "currentStep": None if completed or path != "manual" else (current or TOTAL_STEPS),
            "totalSteps": TOTAL_STEPS,
            "canComplete": not missing and not completed and path is not None,
            "missingRequired": missing,
            "identity": {
                "fullName": person.full_name,
                "email": person.email,
                "phone": person.phone,
            },
            "steps": steps if path == "manual" else [],
            "extractedFacts": extracted,
        }

    async def choose_path(
        self, session: AsyncSession, person: Person, path: OnboardingPath
    ) -> dict[str, Any]:
        self._require_vault(person)
        if person.onboarding_completed_at is not None:
            return await self.status(session, person)
        person.onboarding_path = path
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

    async def _accept_cv_candidates(
        self, session: AsyncSession, person: Person, ids: list[UUID]
    ) -> None:
        from pai.documents.models import DocumentCandidate
        from pai.ingestion.vault_apply import process_candidates
        from pai.orchestration.schemas import VaultCandidate

        result = await session.execute(
            select(DocumentCandidate).where(
                DocumentCandidate.person_id == person.id,
                DocumentCandidate.id.in_(ids),
            )
        )
        to_apply: list[VaultCandidate] = []
        for row in result.scalars():
            row.review_status = "accepted"
            to_apply.append(
                VaultCandidate(
                    field_key=row.field_key,
                    value=row.value,
                    confidence=row.confidence,
                    evidence_text=row.evidence_text or "",
                    source_type="document",
                    source_reference=str(row.document_id),
                    rationale_summary=row.reasoning_summary or "",
                )
            )
        if to_apply:
            await process_candidates(session, person, to_apply, from_document=True)

    async def save_step(
        self,
        session: AsyncSession,
        person: Person,
        step: int,
        payload: OnboardingStep1 | OnboardingStep2 | OnboardingStep3,
    ) -> dict[str, Any]:
        self._require_vault(person)
        if person.onboarding_path is None:
            person.onboarding_path = "manual"
        if isinstance(payload, OnboardingStep1):
            await self._save_step1(session, person, payload)
        elif isinstance(payload, OnboardingStep2):
            await self._save_step2(session, person, payload)
        else:
            await self._save_step3(session, person, payload)
        await self._touch_vault(session, person)
        await session.commit()
        await session.refresh(person)
        return await self.status(session, person)

    async def apply_gap_answers(
        self,
        session: AsyncSession,
        person: Person,
        body: OnboardingGapAnswers,
    ) -> dict[str, Any]:
        self._require_vault(person)
        if body.acceptCandidateIds:
            await self._accept_cv_candidates(session, person, body.acceptCandidateIds)
        await self._apply_gaps(session, person, body)
        await self._touch_vault(session, person)
        await session.commit()
        await session.refresh(person)
        return await self.status(session, person)

    async def complete(self, session: AsyncSession, person: Person) -> dict[str, Any]:
        self._require_vault(person)
        view = await self.status(session, person)
        if view["completed"]:
            return view
        if not person.onboarding_path:
            raise ValidationFailedError(
                "Choose Complete Onboarding or Upload My CV first."
            )
        if view["missingRequired"]:
            raise ValidationFailedError(
                "PAI still needs: " + ", ".join(view["missingRequired"])
            )
        person.onboarding_completed_at = datetime.now(UTC)
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

    async def _save_step1(
        self, session: AsyncSession, person: Person, body: OnboardingStep1
    ) -> None:
        await self._vault.ensure_consent(session, person.id, "demographics")
        await self._vault.upsert_sparse_field(
            session,
            person,
            "demographics.date_of_birth",
            body.dateOfBirth.isoformat(),
            skip_consent_check=True,
        )
        await self._vault.upsert_sparse_field(
            session, person, "demographics.nationality", body.nationality
        )
        await self._vault.upsert_sparse_field(
            session, person, "location.current_country", body.currentCountry
        )
        await self._vault.upsert_sparse_field(
            session, person, "location.current_city", body.currentCity
        )
        await self._vault.upsert_sparse_field(
            session, person, "identity.current_status", body.currentStatus
        )
        if body.gender:
            await self._vault.upsert_sparse_field(
                session, person, "demographics.gender", body.gender
            )
        if body.linkedinUrl:
            await self._vault.upsert_sparse_field(
                session, person, "social.linkedin_url", body.linkedinUrl
            )

    async def _save_step2(
        self, session: AsyncSession, person: Person, body: OnboardingStep2
    ) -> None:
        degree = body.degree or (
            body.otherLevelLabel
            if body.educationLevel == "other"
            else DEGREE_FOR_LEVEL[body.educationLevel]
        )
        await self._vault.upsert_sparse_field(
            session, person, "education.highest_level", body.educationLevel
        )
        row = await self._first_education(session, person)
        if row is None:
            session.add(
                Education(
                    person_id=person.id,
                    institution=body.institution,
                    degree=degree,
                    major=body.major,
                    gpa=body.gpa,
                    graduation_year=body.graduationYear,
                    status="completed",
                )
            )
        else:
            row.institution = body.institution
            row.degree = degree
            if body.major is not None:
                row.major = body.major
            if body.gpa is not None:
                row.gpa = body.gpa
            if body.graduationYear is not None:
                row.graduation_year = body.graduationYear
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "education" not in scopes:
                person.vault.applicable_scopes = scopes + ["education"]

    async def _save_step3(
        self, session: AsyncSession, person: Person, body: OnboardingStep3
    ) -> None:
        await self._upsert_goal(session, person, body.primaryGoal)
        await self._vault.upsert_sparse_field(
            session, person, "application.career_interest", body.primaryGoal
        )
        if body.studyCountry:
            await self._vault.upsert_sparse_field(
                session, person, "application.study_country", body.studyCountry
            )
        if body.intake:
            await self._vault.upsert_sparse_field(
                session, person, "application.admission_cycle", body.intake
            )
        if body.budget:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._vault.upsert_sparse_field(
                session,
                person,
                "finance.funding_status",
                body.budget,
                skip_consent_check=True,
            )
        if body.scholarships is not None:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._vault.upsert_sparse_field(
                session,
                person,
                "finance.scholarship_interest",
                body.scholarships,
                skip_consent_check=True,
            )

    async def _apply_gaps(
        self, session: AsyncSession, person: Person, body: OnboardingGapAnswers
    ) -> None:
        if body.dateOfBirth or body.nationality or body.gender:
            await self._vault.ensure_consent(session, person.id, "demographics")
        if body.dateOfBirth:
            await self._vault.upsert_sparse_field(
                session,
                person,
                "demographics.date_of_birth",
                body.dateOfBirth.isoformat(),
                skip_consent_check=True,
            )
        if body.nationality:
            await self._vault.upsert_sparse_field(
                session, person, "demographics.nationality", body.nationality
            )
        if body.gender:
            await self._vault.upsert_sparse_field(
                session, person, "demographics.gender", body.gender
            )
        if body.currentCountry:
            await self._vault.upsert_sparse_field(
                session, person, "location.current_country", body.currentCountry
            )
        if body.currentCity:
            await self._vault.upsert_sparse_field(
                session, person, "location.current_city", body.currentCity
            )
        if body.currentStatus:
            await self._vault.upsert_sparse_field(
                session, person, "identity.current_status", body.currentStatus
            )
        if body.linkedinUrl:
            await self._vault.upsert_sparse_field(
                session, person, "social.linkedin_url", body.linkedinUrl
            )
        if body.educationLevel:
            await self._vault.upsert_sparse_field(
                session, person, "education.highest_level", body.educationLevel
            )
        if body.institution or body.degree or body.major or body.gpa or body.graduationYear:
            await self._upsert_education_partial(session, person, body)
        if body.primaryGoal:
            await self._upsert_goal(session, person, body.primaryGoal)
            await self._vault.upsert_sparse_field(
                session, person, "application.career_interest", body.primaryGoal
            )
        if body.studyCountry:
            await self._vault.upsert_sparse_field(
                session, person, "application.study_country", body.studyCountry
            )
        if body.intake:
            await self._vault.upsert_sparse_field(
                session, person, "application.admission_cycle", body.intake
            )
        if body.budget:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._vault.upsert_sparse_field(
                session,
                person,
                "finance.funding_status",
                body.budget,
                skip_consent_check=True,
            )
        if body.scholarships is not None:
            await self._vault.ensure_consent(session, person.id, "finance")
            await self._vault.upsert_sparse_field(
                session,
                person,
                "finance.scholarship_interest",
                body.scholarships,
                skip_consent_check=True,
            )

    async def _upsert_education_partial(
        self, session: AsyncSession, person: Person, body: OnboardingGapAnswers
    ) -> None:
        row = await self._first_education(session, person)
        if row is None:
            if not body.institution:
                return
            session.add(
                Education(
                    person_id=person.id,
                    institution=body.institution,
                    degree=body.degree,
                    major=body.major,
                    gpa=body.gpa,
                    graduation_year=body.graduationYear,
                )
            )
            return
        if body.institution:
            row.institution = body.institution
        if body.degree:
            row.degree = body.degree
        if body.major:
            row.major = body.major
        if body.gpa is not None:
            row.gpa = body.gpa
        if body.graduationYear is not None:
            row.graduation_year = body.graduationYear

    async def _upsert_goal(self, session: AsyncSession, person: Person, title: str) -> None:
        row = await self._first_goal(session, person)
        if row is None:
            session.add(
                Goal(
                    person_id=person.id,
                    goal_type="career",
                    title=title[:256],
                    status="active",
                )
            )
        else:
            row.title = title[:256]
            row.status = "active"
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "application" not in scopes:
                person.vault.applicable_scopes = scopes + ["application"]

    def _education_ok(self, education: Education | None) -> bool:
        if education is None or not education.institution:
            return False
        return bool(education.degree or education.major)

    def _missing_required(
        self,
        path: str | None,
        sparse: dict[str, Any],
        snapshot: dict[str, Any],
        education: Education | None,
        goal: Goal | None,
    ) -> list[str]:
        if not path:
            return ["path"]
        active = snapshot.get("active_keys") or set()
        if path == "cv":
            missing: list[str] = []
            if not self._education_ok(education):
                missing.append("institution")
            has_direction = (
                bool(goal and goal.title)
                or _present(_sparse_get(sparse, "application.career_interest"))
                or _present(_sparse_get(sparse, "application.study_country"))
                or "application.study_country" in active
            )
            if not has_direction:
                missing.append("primaryGoal")
            if self._education_ok(education):
                if "application.study_country" not in active:
                    missing.append("studyCountry")
                if "application.admission_cycle" not in active:
                    missing.append("intake")
                if "finance.funding_status" not in active:
                    missing.append("budget")
            return missing
        missing = []
        checks = [
            ("dateOfBirth", _sparse_get(sparse, "demographics.date_of_birth")),
            ("nationality", _sparse_get(sparse, "demographics.nationality")),
            ("currentCountry", _sparse_get(sparse, "location.current_country")),
            ("currentCity", _sparse_get(sparse, "location.current_city")),
            ("currentStatus", _sparse_get(sparse, "identity.current_status")),
            ("educationLevel", _sparse_get(sparse, "education.highest_level")),
        ]
        for name, value in checks:
            if not _present(value):
                missing.append(name)
        if not self._education_ok(education):
            if not education or not education.institution:
                missing.append("institution")
            if not education or not (education.degree or education.major):
                missing.append("degreeOrField")
        if not (goal and goal.title) and not _present(
            _sparse_get(sparse, "application.career_interest")
        ):
            missing.append("primaryGoal")
        return missing

    def _step_view(
        self,
        step: int,
        person: Person,
        sparse: dict[str, Any],
        education: Education | None,
        goal: Goal | None,
    ) -> dict[str, Any]:
        meta = STEP_META[step]
        values, missing = self._step_values(step, person, sparse, education, goal)
        return {
            "step": step,
            "title": meta["title"],
            "complete": not missing,
            "requiredFields": meta["requiredFields"],
            "optionalFields": meta["optionalFields"],
            "missingRequired": missing,
            "values": values,
        }

    def _step_values(
        self,
        step: int,
        person: Person,
        sparse: dict[str, Any],
        education: Education | None,
        goal: Goal | None,
    ) -> tuple[dict[str, Any], list[str]]:
        if step == 1:
            values = {
                "fullName": person.full_name,
                "phone": person.phone,
                "dateOfBirth": _sparse_get(sparse, "demographics.date_of_birth"),
                "nationality": _sparse_get(sparse, "demographics.nationality"),
                "currentCountry": _sparse_get(sparse, "location.current_country"),
                "currentCity": _sparse_get(sparse, "location.current_city"),
                "currentStatus": _sparse_get(sparse, "identity.current_status"),
                "gender": _sparse_get(sparse, "demographics.gender"),
                "linkedinUrl": _sparse_get(sparse, "social.linkedin_url"),
            }
            missing = [
                k
                for k in (
                    "dateOfBirth",
                    "nationality",
                    "currentCountry",
                    "currentCity",
                    "currentStatus",
                )
                if not _present(values[k])
            ]
            return values, missing
        if step == 2:
            values = {
                "educationLevel": _sparse_get(sparse, "education.highest_level"),
                "institution": education.institution if education else None,
                "degree": education.degree if education else None,
                "major": education.major if education else None,
                "gpa": education.gpa if education else None,
                "graduationYear": education.graduation_year if education else None,
            }
            missing: list[str] = []
            if not _present(values["educationLevel"]):
                missing.append("educationLevel")
            if not _present(values["institution"]):
                missing.append("institution")
            if not _present(values["degree"]) and not _present(values["major"]):
                missing.append("degreeOrField")
            return values, missing
        values = {
            "primaryGoal": (goal.title if goal else None)
            or _sparse_get(sparse, "application.career_interest"),
            "studyCountry": _sparse_get(sparse, "application.study_country"),
            "intake": _sparse_get(sparse, "application.admission_cycle"),
            "budget": _sparse_get(sparse, "finance.funding_status"),
            "scholarships": _sparse_get(sparse, "finance.scholarship_interest"),
        }
        missing = ["primaryGoal"] if not _present(values["primaryGoal"]) else []
        return values, missing

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
