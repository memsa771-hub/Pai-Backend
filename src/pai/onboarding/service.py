"""Persist onboarding answers into Person + Person Vault."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.core.errors import AuthError, ValidationFailedError
from pai.onboarding.schema import (
    DEGREE_FOR_LEVEL,
    STEP_META,
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep3,
)
from pai.person.models import Education, Person
from pai.vault.catalog import CATALOG_VERSION
from pai.vault.completion import apply_completion_to_vault, load_presence_snapshot
from pai.vault.service import VaultService

TOTAL_STEPS = 3


def _sparse_get(sparse: dict[str, Any], key: str) -> Any:
    entry = sparse.get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def onboarding_public_status(person: Person | None) -> dict[str, Any]:
    if person is None or person.onboarding_completed_at is None:
        return {"onboardingCompleted": False}
    return {
        "onboardingCompleted": True,
        "onboardingCompletedAt": person.onboarding_completed_at.isoformat(),
    }


class OnboardingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._vault = VaultService(settings or get_settings())

    async def status(self, session: AsyncSession, person: Person) -> dict[str, Any]:
        if person.vault is None:
            raise AuthError(
                code="VAULT_NOT_READY",
                message="Person vault not initialized. Call POST /api/v1/person/bootstrap.",
                status_code=400,
            )
        snapshot = await load_presence_snapshot(session, person, person.vault)
        unified = await self._vault.get_unified_vault(session, person, include_sensitive=True)
        sparse = unified.get("sparseFields") or {}
        first_education = await self._first_education(session, person)
        steps = [
            self._step_view(1, person, sparse, snapshot, first_education),
            self._step_view(2, person, sparse, snapshot, first_education),
            self._step_view(3, person, sparse, snapshot, first_education),
        ]
        current = next((s["step"] for s in steps if not s["complete"]), None)
        missing = [name for s in steps for name in s["missingRequired"]]
        completed = person.onboarding_completed_at is not None
        return {
            "completed": completed,
            "completedAt": (
                person.onboarding_completed_at.isoformat()
                if person.onboarding_completed_at
                else None
            ),
            "currentStep": None if completed else (current or TOTAL_STEPS),
            "totalSteps": TOTAL_STEPS,
            "canComplete": not missing and not completed,
            "missingRequired": missing,
            "steps": steps,
        }

    async def save_step(
        self,
        session: AsyncSession,
        person: Person,
        step: int,
        payload: OnboardingStep1 | OnboardingStep2 | OnboardingStep3,
    ) -> dict[str, Any]:
        self._require_vault(person)
        if isinstance(payload, OnboardingStep1):
            await self._save_step1(session, person, payload)
        elif isinstance(payload, OnboardingStep2):
            await self._save_step2(session, person, payload)
        else:
            await self._save_step3(session, person, payload)
        if person.vault:
            person.vault.catalog_version = CATALOG_VERSION
            await apply_completion_to_vault(session, person, person.vault)
        await session.commit()
        await session.refresh(person)
        return await self.status(session, person)

    async def complete(self, session: AsyncSession, person: Person) -> dict[str, Any]:
        self._require_vault(person)
        view = await self.status(session, person)
        if view["completed"]:
            return view
        if view["missingRequired"]:
            raise ValidationFailedError(
                "Required onboarding fields are missing: " + ", ".join(view["missingRequired"])
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

    async def _save_step1(
        self, session: AsyncSession, person: Person, body: OnboardingStep1
    ) -> None:
        await self._vault.ensure_consent(session, person.id, "demographics")
        person.full_name = body.fullName
        person.version += 1
        await self._vault.upsert_sparse_field(
            session,
            person,
            "demographics.date_of_birth",
            body.dateOfBirth.isoformat(),
            skip_consent_check=True,
        )
        await self._vault.upsert_sparse_field(
            session, person, "demographics.gender", body.gender
        )
        await self._vault.upsert_sparse_field(
            session, person, "demographics.nationality", body.nationality
        )

    async def _save_step2(
        self, session: AsyncSession, person: Person, body: OnboardingStep2
    ) -> None:
        await self._vault.upsert_sparse_field(
            session, person, "location.current_country", body.currentCountry
        )
        await self._vault.upsert_sparse_field(
            session, person, "location.current_city", body.currentCity
        )
        await self._vault.upsert_sparse_field(
            session, person, "identity.current_status", body.currentStatus
        )
        if body.nationalId:
            await self._vault.ensure_consent(session, person.id, "identity")
            await self._vault.upsert_sparse_field(
                session,
                person,
                "identity.national_id",
                body.nationalId,
                skip_consent_check=True,
            )
        if body.linkedinUrl:
            await self._vault.upsert_sparse_field(
                session, person, "social.linkedin_url", body.linkedinUrl
            )

    async def _save_step3(
        self, session: AsyncSession, person: Person, body: OnboardingStep3
    ) -> None:
        degree = body.degree or (
            body.otherLevelLabel
            if body.educationLevel == "other"
            else DEGREE_FOR_LEVEL[body.educationLevel]
        )
        await self._vault.upsert_sparse_field(
            session, person, "education.highest_level", body.educationLevel
        )
        result = await session.execute(
            select(Education)
            .where(Education.person_id == person.id)
            .order_by(Education.created_at.asc())
        )
        row = result.scalars().first()
        if row is None:
            session.add(
                Education(
                    person_id=person.id,
                    institution=body.institution,
                    degree=degree,
                    major=body.major,
                    graduation_year=body.graduationYear,
                    status="completed",
                )
            )
        else:
            row.institution = body.institution
            row.degree = degree
            if body.major is not None:
                row.major = body.major
            if body.graduationYear is not None:
                row.graduation_year = body.graduationYear
        if person.vault:
            scopes = list(person.vault.applicable_scopes or [])
            if "education" not in scopes:
                person.vault.applicable_scopes = scopes + ["education"]

    async def _first_education(
        self, session: AsyncSession, person: Person
    ) -> Education | None:
        result = await session.execute(
            select(Education)
            .where(Education.person_id == person.id)
            .order_by(Education.created_at.asc())
        )
        return result.scalars().first()

    def _step_view(
        self,
        step: int,
        person: Person,
        sparse: dict[str, Any],
        snapshot: dict[str, Any],
        education: Education | None,
    ) -> dict[str, Any]:
        meta = STEP_META[step]
        values, missing = self._step_values(step, person, sparse, snapshot, education)
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
        snapshot: dict[str, Any],
        education: Education | None,
    ) -> tuple[dict[str, Any], list[str]]:
        if step == 1:
            values = {
                "fullName": person.full_name,
                "dateOfBirth": _sparse_get(sparse, "demographics.date_of_birth"),
                "gender": _sparse_get(sparse, "demographics.gender"),
                "nationality": _sparse_get(sparse, "demographics.nationality"),
            }
            missing = [k for k, v in values.items() if v in (None, "")]
            return values, missing
        if step == 2:
            values = {
                "currentCountry": _sparse_get(sparse, "location.current_country"),
                "currentCity": _sparse_get(sparse, "location.current_city"),
                "currentStatus": _sparse_get(sparse, "identity.current_status"),
                "nationalId": _sparse_get(sparse, "identity.national_id"),
                "linkedinUrl": _sparse_get(sparse, "social.linkedin_url"),
            }
            missing = [
                k
                for k in ("currentCountry", "currentCity", "currentStatus")
                if values[k] in (None, "")
            ]
            return values, missing
        educations_present = bool(snapshot["typed_present"].get("educations")) or (
            education is not None
        )
        level = _sparse_get(sparse, "education.highest_level")
        values = {
            "educationLevel": level,
            "institution": education.institution if education else None,
            "degree": education.degree if education else None,
            "major": education.major if education else None,
            "graduationYear": education.graduation_year if education else None,
            "hasEducationRecord": educations_present,
        }
        missing: list[str] = []
        if not level:
            missing.append("educationLevel")
        if not educations_present:
            missing.append("institution")
        return values, missing
