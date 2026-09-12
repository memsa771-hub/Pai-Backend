"""Seed a small Person profile. Chat, documents, and later updates enrich the Vault."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.kernel.errors import AuthError, ValidationFailedError
from pai.workflows.onboarding.catalog import (
    COUNTRY_FIELDS,
    GOAL_TYPE_FOR_PRIMARY,
    PRIMARY_GOAL_TITLES,
    PrimaryGoal,
    field_enum_catalog,
)
from pai.workflows.onboarding.contracts import (
    CONDITIONAL_FIELDS,
    ONBOARDING_PURPOSE,
    OPTIONAL_FIELDS,
    PATH_CHOICES,
    REQUIRED_FIELDS,
    OnboardingSubmit,
)
from pai.domains.goals.models import Goal
from pai.domains.goals.service import enqueue_goal_intelligence_job, upsert_goal_from_anchors
from pai.domains.goals.types import GoalWriteAction
from pai.domains.student.person.models import Person
from pai.domains.student.vault.service import VaultService, grow_vault_schema


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

    def _result(self, person: Person) -> dict[str, Any]:
        payload = onboarding_public_status(person, self._settings)
        payload["completed"] = payload["onboardingCompleted"]
        payload["path"] = payload["onboardingPath"]
        if "onboardingCompletedAt" in payload:
            payload["completedAt"] = payload["onboardingCompletedAt"]
        payload["identity"] = {
            "fullName": person.full_name,
            "email": person.email,
            "phone": person.phone,
        }
        return payload

    async def status(self, session: AsyncSession, person: Person) -> dict[str, Any]:
        self._require_vault(person)
        if person.onboarding_completed_at is not None:
            return self._result(person)
        sparse = await self._vault.get_sparse_fields(
            session, person, include_sensitive=True
        )
        goal = await self._first_goal(session, person)
        values = self._current_values(person, sparse, goal)
        missing = self._missing_required(values)
        public = onboarding_public_status(person, self._settings)
        return {
            **public,
            "completed": False,
            "path": person.onboarding_path,
            "choices": PATH_CHOICES if not person.onboarding_path else [],
            "purpose": ONBOARDING_PURPOSE,
            "vaultEnrichment": "chat_and_documents",
            "canComplete": not missing,
            "missingRequired": missing,
            "requiredFields": REQUIRED_FIELDS,
            "conditionalFields": CONDITIONAL_FIELDS,
            "optionalFields": OPTIONAL_FIELDS,
            "countryFields": list(COUNTRY_FIELDS),
            "enums": field_enum_catalog(),
            "identity": {
                "fullName": person.full_name,
                "email": person.email,
                "phone": person.phone,
            },
            "values": values,
        }

    async def submit(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> dict[str, Any]:
        """Map the starting profile into the Vault and mark onboarding complete. Idempotent."""
        from pai.domains.student.person.write_lock import lock_person
        await lock_person(session, person.id)
        self._require_vault(person)
        person.onboarding_path = body.path or person.onboarding_path or "manual"
        await self._apply_submit(session, person, body)
        await self._touch_vault(session, person)
        from pai.domains.goals.service import mark_intelligence_stale_for_vault_update
        await mark_intelligence_stale_for_vault_update(session, person.id, "onboarding")
        if person.onboarding_completed_at is None:
            person.onboarding_completed_at = datetime.now(UTC)
        from pai.domains.journey.service import record_onboarding

        title = PRIMARY_GOAL_TITLES[body.primaryGoal.value]
        await record_onboarding(session, person.id, intent=title)
        await session.commit()
        return self._result(person)

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
        """Extract CV facts into the vault and mark onboarding complete."""
        self._require_vault(person)
        person.onboarding_path = "cv"
        from pai.domains.documents.models import DocumentJob
        from pai.intelligences.documents.ingest import create_document_upload
        from pai.intelligences.documents.workers.analysis_worker import process_document_job

        doc = await create_document_upload(
            session,
            self._settings,
            person,
            filename=filename,
            content_type=content_type,
            data=data,
            storage=storage,
            source_type="onboarding",
            inline_processing=True,
            document_type="resume",
            created_by="student",
        )
        result = await session.execute(
            select(DocumentJob)
            .where(DocumentJob.document_id == doc.id)
            .order_by(DocumentJob.created_at.desc())
        )
        job = result.scalars().first()
        if job is None:
            raise AuthError(
                code="CV_EXTRACT_FAILED",
                message="CV upload was saved but no extraction job was created.",
                status_code=502,
            )
        try:
            from pai.platform.jobs.lease import pin_lease
            if not await pin_lease(session, job):
                raise AuthError("CV_PROCESSING", "Your CV is already being processed.", 409)
            await process_document_job(
                session, self._settings, job, storage=storage, gateway=gateway
            )
            await session.commit()
        except AuthError:
            raise
        except Exception as exc:
            job_id = job.id
            await session.rollback()
            job = await session.get(DocumentJob, job_id)
            job.status = "failed"
            job.last_error = str(exc)[:500]
            await session.commit()
            raise AuthError(
                code="CV_EXTRACT_FAILED",
                message="Could not extract your CV. Try a text-based PDF or DOCX.",
                status_code=502,
            ) from exc
        if job.status == "failed":
            raise ValidationFailedError(
                job.last_error
                or (
                    "Could not read text from this file. "
                    "Upload a text-based PDF or DOCX, not a scan."
                )
            )
        if person.onboarding_completed_at is None:
            person.onboarding_completed_at = datetime.now(UTC)
        await self._touch_vault(session, person)
        from pai.domains.journey.service import record_onboarding

        goal = await self._first_goal(session, person)
        await record_onboarding(session, person.id, intent=goal.title if goal else None)
        await session.commit()
        return self._result(person)

    def _require_vault(self, person: Person) -> None:
        if person.vault is None:
            raise AuthError(
                code="VAULT_NOT_READY",
                message="Person vault not initialized. Call POST /api/v1/person/bootstrap.",
                status_code=400,
            )

    async def _touch_vault(self, session: AsyncSession, person: Person) -> None:
        if person.vault:
            grow_vault_schema(person.vault)

    async def _apply_submit(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        if body.phone:
            person.phone = body.phone
        if body.fullName:
            person.full_name = body.fullName
        consents = ["demographics"]
        await self._vault.ensure_consents(session, person.id, consents)

        updates: list[tuple[str, Any]] = [
            ("demographics.date_of_birth", body.dateOfBirth.isoformat()),
            ("demographics.gender", body.gender.value),
            ("identity.current_status", body.currentStatus.value),
        ]
        if body.nationality:
            updates.append(("demographics.nationality", body.nationality))
        if body.currentCountry:
            updates.append(("location.current_country", body.currentCountry))
        if body.currentCity:
            updates.append(("location.current_city", body.currentCity))

        await self._vault.upsert_sparse_fields(
            session, person, updates, skip_consent_check=True
        )
        await self._upsert_goal(session, person, body)

    async def _upsert_goal(
        self, session: AsyncSession, person: Person, body: OnboardingSubmit
    ) -> None:
        goal_key = body.primaryGoal.value
        title = PRIMARY_GOAL_TITLES[goal_key]
        goal_type = GOAL_TYPE_FOR_PRIMARY[goal_key]
        anchors: dict[str, Any] = {"goal_type": goal_type, "title": title}
        goal, action = await upsert_goal_from_anchors(
            session,
            person.id,
            goal_type=goal_type,
            title=title,
            anchors=anchors,
            activate=True,
        )
        if goal is not None:
            goal.description = goal_key
            if action != GoalWriteAction.REINFORCE:
                await enqueue_goal_intelligence_job(session, goal)
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "application" not in scopes:
                person.vault.applicable_scopes = scopes + ["application"]

    def _current_values(
        self,
        person: Person,
        sparse: dict[str, Any],
        goal: Goal | None,
    ) -> dict[str, Any]:
        return {
            "fullName": person.full_name,
            "phone": person.phone,
            "dateOfBirth": _sparse_get(sparse, "demographics.date_of_birth"),
            "gender": _sparse_get(sparse, "demographics.gender"),
            "currentStatus": _sparse_get(sparse, "identity.current_status"),
            "primaryGoal": (
                goal.description
                if goal and goal.description in {item.value for item in PrimaryGoal}
                else None
            ),
            "nationality": _sparse_get(sparse, "demographics.nationality"),
            "currentCountry": _sparse_get(sparse, "location.current_country"),
            "currentCity": _sparse_get(sparse, "location.current_city"),
        }

    def _missing_required(self, values: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for name in REQUIRED_FIELDS:
            if not _present(values.get(name)):
                missing.append(name)
        return missing

    async def _first_goal(self, session: AsyncSession, person: Person) -> Goal | None:
        result = await session.execute(
            select(Goal)
            .where(Goal.person_id == person.id)
            .order_by(Goal.created_at.asc())
        )
        return result.scalars().first()

