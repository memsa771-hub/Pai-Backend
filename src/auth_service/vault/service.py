from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.config import Settings, get_settings
from auth_service.core.errors import (
    ConsentRequiredError,
    FieldNotEditableError,
    UnknownFieldError,
    VersionConflictError,
)
from auth_service.person.models import (
    Person,
    PersonConsent,
    PersonVault,
    VaultEvidence,
    VaultHistory,
    VaultValue,
)
from auth_service.vault.catalog import get_catalog_field
from auth_service.vault.completion import apply_completion_to_vault, compute_completion
from auth_service.vault.security import SensitiveValueCodec, mask_value


class VaultService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._codec = SensitiveValueCodec(self._settings.vault_encryption_key)

    async def get_unified_vault(
        self,
        session: AsyncSession,
        person: Person,
        *,
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        vault = person.vault
        if vault is None:
            return {"fields": {}, "typed": {}, "completion": {}}
        from auth_service.vault.completion import load_presence_snapshot

        consents = await self._consent_map(session, person.id)
        sparse = await self._load_sparse_fields(session, vault, consents, include_sensitive)
        # One presence snapshot feeds typed counts + completion (no duplicate N+1).
        snapshot = await load_presence_snapshot(session, person, vault)
        typed = snapshot.get("typed_resources") or await self._load_typed_summary(
            session, person.id
        )
        completion = await compute_completion(session, person, vault, snapshot=snapshot)
        return {
            "vaultId": str(vault.id),
            "catalogVersion": vault.catalog_version,
            "applicableScopes": vault.applicable_scopes,
            "sparseFields": sparse,
            "typedResources": typed,
            "completion": completion,
            "version": vault.version,
        }

    async def set_field(
        self,
        session: AsyncSession,
        person: Person,
        field_key: str,
        value: Any,
        *,
        expected_version: int | None,
    ) -> dict[str, Any]:
        field = get_catalog_field(field_key)
        if field is None:
            raise UnknownFieldError()
        if field.derived or not field.editable:
            raise FieldNotEditableError()
        if field.storage != "vault_value":
            raise FieldNotEditableError("Update the typed profile resource for this field.")
        if field.consent_category and not await self._has_consent(session, person.id, field.consent_category):
            raise ConsentRequiredError()

        vault = person.vault
        if vault is None:
            raise UnknownFieldError("Vault not initialized.")
        if expected_version is not None and vault.version != expected_version:
            raise VersionConflictError()

        async with session.begin():
            result = await session.execute(
                select(VaultValue).where(
                    VaultValue.vault_id == vault.id,
                    VaultValue.field_key == field_key,
                    VaultValue.status == "active",
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.status = "superseded"
                old_val = existing.value
            else:
                old_val = None

            row = VaultValue(
                vault_id=vault.id,
                field_key=field_key,
                value=None if field.sensitive else value,
                value_encrypted=self._codec.encrypt_json(value) if field.sensitive else None,
                status="active",
                verification_level="self_reported",
                confidence=1.0,
                supersedes_id=existing.id if existing else None,
            )
            session.add(row)
            await session.flush()
            session.add(
                VaultEvidence(
                    vault_value_id=row.id,
                    source_type="manual",
                    source_reference=str(person.id),
                    confidence=1.0,
                )
            )
            session.add(
                VaultHistory(
                    vault_id=vault.id,
                    field_key=field_key,
                    action="updated" if old_val is not None else "created",
                    old_value=old_val,
                    new_value=value,
                    actor_type="person",
                    actor_id=str(person.id),
                )
            )
            await self._maybe_expand_scopes(session, vault, field.applicable_scope)
            await apply_completion_to_vault(session, person, vault)

        return await self.get_field(session, person, field_key, include_sensitive=True)

    async def delete_field(
        self,
        session: AsyncSession,
        person: Person,
        field_key: str,
        *,
        expected_version: int | None,
    ) -> None:
        field = get_catalog_field(field_key)
        if field is None:
            raise UnknownFieldError()
        if field.derived or not field.editable or field.storage != "vault_value":
            raise FieldNotEditableError()
        vault = person.vault
        if vault is None:
            return
        if expected_version is not None and vault.version != expected_version:
            raise VersionConflictError()
        async with session.begin():
            result = await session.execute(
                select(VaultValue).where(
                    VaultValue.vault_id == vault.id,
                    VaultValue.field_key == field_key,
                    VaultValue.status == "active",
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                return
            existing.status = "deleted"
            session.add(
                VaultHistory(
                    vault_id=vault.id,
                    field_key=field_key,
                    action="deleted",
                    old_value=existing.value,
                    new_value=None,
                    actor_type="person",
                    actor_id=str(person.id),
                )
            )
            await apply_completion_to_vault(session, person, vault)

    async def get_field(
        self,
        session: AsyncSession,
        person: Person,
        field_key: str,
        *,
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        field = get_catalog_field(field_key)
        if field is None:
            raise UnknownFieldError()
        if field.storage == "person" and field.person_column:
            raw = getattr(person, field.person_column)
            return {"key": field_key, "value": raw, "masked": False}
        vault = person.vault
        if vault is None:
            return {"key": field_key, "value": None, "masked": False}
        result = await session.execute(
            select(VaultValue).where(
                VaultValue.vault_id == vault.id,
                VaultValue.field_key == field_key,
                VaultValue.status == "active",
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return {"key": field_key, "value": None, "masked": False}
        if field.sensitive and not include_sensitive:
            return {"key": field_key, "value": mask_value(row.value), "masked": True}
        value = row.value
        if row.value_encrypted:
            value = self._codec.decrypt_json(row.value_encrypted)
        return {
            "key": field_key,
            "value": value,
            "verificationLevel": row.verification_level,
            "masked": False,
        }

    async def field_history(
        self, session: AsyncSession, person: Person, field_key: str
    ) -> list[dict[str, Any]]:
        if person.vault is None:
            return []
        result = await session.execute(
            select(VaultHistory)
            .where(VaultHistory.vault_id == person.vault.id, VaultHistory.field_key == field_key)
            .order_by(VaultHistory.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "action": r.action,
                "oldValue": r.old_value,
                "newValue": r.new_value,
                "actorType": r.actor_type,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def _load_sparse_fields(
        self,
        session: AsyncSession,
        vault: PersonVault,
        consents: dict[str, bool],
        include_sensitive: bool,
    ) -> dict[str, Any]:
        result = await session.execute(
            select(VaultValue).where(
                VaultValue.vault_id == vault.id,
                VaultValue.status == "active",
            )
        )
        out: dict[str, Any] = {}
        for row in result.scalars():
            field = get_catalog_field(row.field_key)
            if field is None:
                continue
            if field.sensitive:
                if field.consent_category and not consents.get(field.consent_category):
                    out[row.field_key] = mask_value(None)
                    continue
                if not include_sensitive:
                    out[row.field_key] = mask_value(None)
                    continue
                if row.value_encrypted:
                    out[row.field_key] = self._codec.decrypt_json(row.value_encrypted)
                else:
                    out[row.field_key] = row.value
            else:
                out[row.field_key] = row.value
        return out

    async def _load_typed_summary(self, session: AsyncSession, person_id: uuid.UUID) -> dict[str, str]:
        from sqlalchemy import func

        from auth_service.person.models import (
            Certification,
            Education,
            Goal,
            Project,
            Skill,
            WorkExperience,
        )

        # Single round-trip style: sequential counts but shared with completion snapshot
        # when callers use load_presence_snapshot — keep API shape stable.
        models = [
            ("educations", Education),
            ("workExperiences", WorkExperience),
            ("projects", Project),
            ("skills", Skill),
            ("certifications", Certification),
            ("goals", Goal),
        ]
        summary: dict[str, str] = {}
        for name, model in models:
            count = await session.scalar(
                select(func.count()).select_from(model).where(model.person_id == person_id)
            )
            summary[name] = str(count or 0)
        return summary

    async def _consent_map(self, session: AsyncSession, person_id: uuid.UUID) -> dict[str, bool]:
        result = await session.execute(
            select(PersonConsent).where(PersonConsent.person_id == person_id)
        )
        return {row.category: row.granted for row in result.scalars()}

    async def _has_consent(self, session: AsyncSession, person_id: uuid.UUID, category: str) -> bool:
        result = await session.execute(
            select(PersonConsent).where(
                PersonConsent.person_id == person_id,
                PersonConsent.category == category,
                PersonConsent.granted.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    async def _maybe_expand_scopes(
        self, session: AsyncSession, vault: PersonVault, scope: str
    ) -> None:
        scopes = list(vault.applicable_scopes or [])
        if scope not in scopes:
            scopes.append(scope)
            vault.applicable_scopes = scopes


async def expand_scope_for_person(
    session: AsyncSession, person: Person, scope: str
) -> None:
    if person.vault is None:
        return
    scopes = list(person.vault.applicable_scopes or [])
    if scope not in scopes:
        person.vault.applicable_scopes = scopes + [scope]
        await apply_completion_to_vault(session, person, person.vault)
