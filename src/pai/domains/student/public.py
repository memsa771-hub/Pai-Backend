"""Public Vault reads. ORM rows never escape this boundary.

The caller supplies an authenticated owner ID and owns the transaction. Reads
exclude deleted accounts and sensitive fields; publication uses the same write
fence as canonical student mutations.
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pai.domains.student.person.models import Person, Education, PersonVault, VaultValue
from pai.domains.student.person.profile_snapshot import load_typed_profile_records
from pai.domains.student.person.write_lock import lock_person
from pai.domains.student.vault.catalog import VAULT_CATALOG, get_catalog_field
from pai.domains.student.vault.service import VaultService
from pai.kernel.contracts.vault import VaultSnapshot, StudentIdentity


def assessment_input(records: dict) -> dict:
    aliases = {"workExperiences": "work_experiences"}
    snapshot = {aliases.get(key, key): value for key, value in records.items()
                if key not in {"counts", "sparseFields", "goals"}}
    sparse = records.get("sparseFields") or {}
    for field in VAULT_CATALOG.values():
        if not field.sensitive and field.storage == "vault_value":
            snapshot[field.key] = sparse.get(field.key)
    return snapshot


def dependency_key(field_key: str) -> str:
    field = get_catalog_field(field_key)
    return field.storage if field and field.storage not in {"vault_value", "person"} else field_key


async def lock_owner(session, person_id):
    """Fence deletion and writes without exposing the locked ORM row."""
    person = await lock_person(session, person_id)
    return person.vault.version if person.vault else None


async def refresh_profile_projection(session, person_id, *, scopes=()):
    from pai.domains.student.vault.service import expand_scope_for_person
    from pai.domains.student.vault.completion import apply_completion_to_vault
    person = await lock_person(session, person_id)
    for scope in scopes:
        await expand_scope_for_person(session, person, scope)
    if person.vault:
        await apply_completion_to_vault(session, person, person.vault)


class VaultReader:
    def __init__(self, session, settings=None):
        self.session = session
        self.service = VaultService(settings)

    async def get_snapshot(self, person_id):
        person = (await self.session.execute(
            select(Person).options(selectinload(Person.vault)).where(
                Person.id == person_id, Person.deleted_at.is_(None)
            )
        )).scalar_one_or_none()
        if person is None:
            return None
        records = await load_typed_profile_records(self.session, person_id, include_goals=False)
        unified = await self.service.get_unified_vault(
            self.session, person, include_sensitive=False, typed_records=records
        )
        completion = unified.get("completion") or {}
        missing = list(dict.fromkeys(
            key for name in ("missingCriticalFields", "missingImportantFields", "missingEnrichmentFields")
            for key in completion.get(name, [])
        ))
        return VaultSnapshot(
            person_id=person_id, revision=person.vault.version if person.vault else None,
            profile=assessment_input({**records, "sparseFields": unified.get("sparseFields") or {}}),
            completion=completion, missing=missing,
        )

    async def get_identity(self, person_id):
        row = (await self.session.execute(select(Person.id, Person.full_name, Person.preferred_name).where(
            Person.id == person_id, Person.deleted_at.is_(None)
        ))).one_or_none()
        return StudentIdentity(id=row.id, full_name=row.full_name, preferred_name=row.preferred_name) if row else None

    async def get_known_facts(self, person_id):
        from pai.domains.student.facts import build_known_facts
        identity = await self.get_identity(person_id)
        snapshot = await self.get_snapshot(person_id)
        if identity is None or snapshot is None:
            return []
        return build_known_facts(
            identity={"preferredName": identity.preferred_name, "fullName": identity.full_name},
            sparse=snapshot.profile, typed=snapshot.profile,
        )

    async def get_existing_belief(self, person_id, field_key, *, spec=None):
        """Read reconciliation inputs, including unsettled sparse claims."""
        identity = await self.get_identity(person_id)
        if identity is None:
            return None
        field = get_catalog_field(field_key)
        if field is not None and field.storage == "person" and field.person_column:
            value = await self.session.scalar(select(getattr(Person, field.person_column)).where(Person.id == person_id))
            return value or identity.preferred_name
        spec = spec or {}
        if spec.get("storage") == "educations":
            row = await self.session.scalar(select(Education).where(Education.person_id == person_id).order_by(Education.updated_at.desc()).limit(1))
            raw = getattr(row, str(spec.get("column") or "gpa"), None) if row else None
            if raw is None:
                return None
            scale = getattr(row, str(spec["scale_column"]), None) if spec.get("scale_column") else None
            if spec.get("shape") == "cumulative_gpa":
                return {"value": float(raw), "scale": float(scale) if scale is not None else None, "type": "cumulative"}
            return raw
        return await self.session.scalar(select(VaultValue.value).join(PersonVault, PersonVault.id == VaultValue.vault_id).where(
            PersonVault.person_id == person_id, VaultValue.field_key == field_key,
            VaultValue.status.in_(("active", "pending_confirmation", "disputed")),
        ))

    async def lock_revision(self, person_id):
        person = await lock_person(self.session, person_id)
        return person.vault.version if person.vault else None

    async def get_completion(self, person_id):
        snapshot = await self.get_snapshot(person_id)
        return snapshot.completion if snapshot else None

    async def get_missing(self, person_id):
        snapshot = await self.get_snapshot(person_id)
        return snapshot.missing if snapshot else None


class VaultWriter:
    """Preserve canonical evidence gates and the caller's transaction."""

    def __init__(self, session):
        self.session = session

    async def submit_observations(self, person_id, observations, **policy):
        from pai.kernel.gates import accept_vault_candidates
        person = await lock_person(self.session, person_id)
        return await accept_vault_candidates(self.session, person, observations, **policy)

    async def submit_document_evidence(self, evidence, *, already_reconciled=False, apply_order=None):
        if any(row.source_type != "document" or row.source_reference != str(evidence.document_id)
               for row in evidence.observations):
            raise ValueError("Document evidence source does not match its envelope")
        return await self.submit_observations(
            evidence.person_id, evidence.observations, from_document=True,
            already_reconciled=already_reconciled, apply_order=apply_order,
        )
