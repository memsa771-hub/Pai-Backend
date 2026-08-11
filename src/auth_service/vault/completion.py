from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.person.models import (
    Certification,
    Education,
    Goal,
    Person,
    PersonVault,
    Project,
    Skill,
    VaultValue,
    WorkExperience,
)
from auth_service.vault.catalog import VAULT_CATALOG, CatalogField, Priority

# (storage_key used by catalog, ORM model, API camelCase for typedResources)
_TYPED_MODELS: list[tuple[str, type, str]] = [
    ("educations", Education, "educations"),
    ("work_experiences", WorkExperience, "workExperiences"),
    ("projects", Project, "projects"),
    ("skills", Skill, "skills"),
    ("certifications", Certification, "certifications"),
    ("goals", Goal, "goals"),
]


def _scope_fields(scopes: list[str]) -> list[CatalogField]:
    applicable = set(scopes)
    return [f for f in VAULT_CATALOG.values() if f.applicable_scope in applicable]


def priority_name(p: Priority) -> str:
    return {"C": "critical", "I": "important", "E": "enrichment"}[p]


async def load_presence_snapshot(
    session: AsyncSession,
    person: Person,
    vault: PersonVault | None,
) -> dict[str, Any]:
    """One-shot DB snapshot for completion / status (no per-field N+1)."""
    active_keys: set[str] = set()
    if vault is not None:
        result = await session.execute(
            select(VaultValue.field_key).where(
                VaultValue.vault_id == vault.id,
                VaultValue.status == "active",
            )
        )
        active_keys = set(result.scalars().all())

    typed_counts: dict[str, int] = {}
    typed_present: dict[str, bool] = {}
    typed_resources: dict[str, str] = {}
    for storage_key, model, api_name in _TYPED_MODELS:
        count = await session.scalar(
            select(func.count()).select_from(model).where(model.person_id == person.id)
        )
        n = int(count or 0)
        typed_counts[storage_key] = n
        typed_present[storage_key] = n > 0
        typed_resources[api_name] = str(n)

    return {
        "active_keys": active_keys,
        "typed_present": typed_present,
        "typed_counts": typed_counts,
        "typed_resources": typed_resources,
    }


def field_is_present_in_snapshot(
    person: Person,
    field: CatalogField,
    snapshot: dict[str, Any],
) -> bool:
    if field.storage == "person":
        col = field.person_column
        if not col:
            return False
        return getattr(person, col) not in (None, "")
    if field.storage == "vault_value":
        return field.key in snapshot["active_keys"]
    return bool(snapshot["typed_present"].get(field.storage, False))


async def field_is_present(
    session: AsyncSession,
    person: Person,
    field: CatalogField,
) -> bool:
    """Compatibility helper — prefer batch snapshot for hot paths."""
    snapshot = await load_presence_snapshot(session, person, person.vault)
    return field_is_present_in_snapshot(person, field, snapshot)


def compute_completion_from_snapshot(
    person: Person,
    vault: PersonVault,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    scopes: list[str] = list(vault.applicable_scopes or ["universal"])
    fields = _scope_fields(scopes)
    by_priority: dict[Priority, list[CatalogField]] = {"C": [], "I": [], "E": []}
    for field in fields:
        by_priority[field.priority].append(field)

    missing_critical: list[str] = []
    scores: dict[str, int] = {}
    present_map: dict[str, bool] = {}

    for field in fields:
        present_map[field.key] = field_is_present_in_snapshot(person, field, snapshot)

    for priority in ("C", "I", "E"):
        group = by_priority[priority]
        if not group:
            scores[priority_name(priority)] = 0
            continue
        filled = sum(1 for f in group if present_map[f.key])
        scores[priority_name(priority)] = round(100 * filled / len(group))
        if priority == "C":
            missing_critical = [f.key for f in group if not present_map[f.key]]

    overall = (
        round(100 * sum(1 for f in fields if present_map[f.key]) / len(fields)) if fields else 0
    )

    next_field: dict[str, Any] = {}
    for field in sorted(fields, key=lambda f: (f.priority, f.key)):
        if not present_map[field.key]:
            next_field = {"key": field.key, "priority": field.priority, "section": field.section}
            break

    return {
        "critical": scores.get("critical", 0),
        "important": scores.get("important", 0),
        "enrichment": scores.get("enrichment", 0),
        "overall": overall,
        "applicableScopes": scopes,
        "missingCriticalFields": missing_critical,
        "nextRecommendedField": next_field,
        "_present_map": present_map,
    }


async def compute_completion(
    session: AsyncSession,
    person: Person,
    vault: PersonVault,
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snap = snapshot or await load_presence_snapshot(session, person, vault)
    result = compute_completion_from_snapshot(person, vault, snap)
    result.pop("_present_map", None)
    return result


async def build_vault_status(
    session: AsyncSession,
    person: Person,
    *,
    include_sensitive: bool = False,
) -> dict[str, Any]:
    """Simple filled/missing overview for after-chat UX."""
    vault = person.vault
    if vault is None:
        return {
            "completion": {"critical": 0, "important": 0, "enrichment": 0, "overall": 0},
            "filled": [],
            "missing": [],
            "nextRecommendedField": {},
            "filledCount": 0,
            "missingCount": 0,
        }

    from auth_service.vault.service import VaultService

    unified = await VaultService().get_unified_vault(
        session, person, include_sensitive=include_sensitive
    )
    sparse = unified.get("sparseFields") or {}
    completion = unified.get("completion") or {}
    typed = unified.get("typedResources") or {}
    typed_present = {
        "educations": int(typed.get("educations") or 0) > 0,
        "work_experiences": int(typed.get("workExperiences") or 0) > 0,
        "projects": int(typed.get("projects") or 0) > 0,
        "skills": int(typed.get("skills") or 0) > 0,
        "certifications": int(typed.get("certifications") or 0) > 0,
        "goals": int(typed.get("goals") or 0) > 0,
    }
    snapshot = {"active_keys": set(sparse.keys()), "typed_present": typed_present}
    scopes: list[str] = list(vault.applicable_scopes or ["universal"])
    fields = _scope_fields(scopes)

    filled: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for field in sorted(fields, key=lambda f: (f.priority, f.key)):
        present = field_is_present_in_snapshot(person, field, snapshot)
        item = {
            "key": field.key,
            "section": field.section,
            "priority": field.priority,
            "priorityLabel": priority_name(field.priority),
            "sensitive": field.sensitive,
        }
        if present:
            if field.storage == "vault_value" and field.key in sparse:
                entry = sparse[field.key]
                item["value"] = entry["value"] if isinstance(entry, dict) and "value" in entry else entry
            elif field.storage == "person" and field.person_column:
                raw = getattr(person, field.person_column, None)
                item["value"] = "[sensitive]" if field.sensitive and not include_sensitive else raw
            else:
                item["value"] = True
            filled.append(item)
        else:
            missing.append(item)

    return {
        "completion": {
            "critical": completion.get("critical", 0),
            "important": completion.get("important", 0),
            "enrichment": completion.get("enrichment", 0),
            "overall": completion.get("overall", 0),
        },
        "filledCount": len(filled),
        "missingCount": len(missing),
        "filled": filled,
        "missing": missing,
        "nextRecommendedField": completion.get("nextRecommendedField") or {},
    }


async def apply_completion_to_vault(
    session: AsyncSession,
    person: Person,
    vault: PersonVault,
) -> dict[str, Any]:
    result = await compute_completion(session, person, vault)
    vault.critical_completion = result["critical"]
    vault.important_completion = result["important"]
    vault.enrichment_completion = result["enrichment"]
    vault.overall_completion = result["overall"]
    vault.version += 1
    return result
