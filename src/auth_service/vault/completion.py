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


def _scope_fields(scopes: list[str]) -> list[CatalogField]:
    applicable = set(scopes)
    return [f for f in VAULT_CATALOG.values() if f.applicable_scope in applicable]


def _typed_count(session_query) -> bool:
    return session_query  # placeholder - async checks in compute


async def field_is_present(
    session: AsyncSession,
    person: Person,
    field: CatalogField,
) -> bool:
    if field.storage == "person":
        col = field.person_column
        if not col:
            return False
        return getattr(person, col) not in (None, "")
    if field.storage == "vault_value":
        if not person.vault:
            return False
        result = await session.execute(
            select(VaultValue.id).where(
                VaultValue.vault_id == person.vault.id,
                VaultValue.field_key == field.key,
                VaultValue.status == "active",
            )
        )
        return result.scalar_one_or_none() is not None
    table_map = {
        "educations": Education,
        "work_experiences": WorkExperience,
        "projects": Project,
        "skills": Skill,
        "certifications": Certification,
        "goals": Goal,
    }
    model = table_map.get(field.storage)
    if model is None:
        return False
    result = await session.execute(
        select(func.count()).select_from(model).where(model.person_id == person.id)
    )
    return (result.scalar() or 0) > 0


async def compute_completion(
    session: AsyncSession,
    person: Person,
    vault: PersonVault,
) -> dict[str, Any]:
    scopes: list[str] = list(vault.applicable_scopes or ["universal"])
    fields = _scope_fields(scopes)
    by_priority: dict[Priority, list[CatalogField]] = {"C": [], "I": [], "E": []}
    for field in fields:
        by_priority[field.priority].append(field)

    missing_critical: list[str] = []
    scores: dict[str, int] = {}

    for priority in ("C", "I", "E"):
        group = by_priority[priority]
        if not group:
            scores[priority_name(priority)] = 0
            continue
        filled = 0
        for field in group:
            present = await field_is_present(session, person, field)
            if present:
                filled += 1
            elif priority == "C":
                missing_critical.append(field.key)
        scores[priority_name(priority)] = round(100 * filled / len(group))

    overall_fields = fields
    if overall_fields:
        total = 0
        for field in overall_fields:
            if await field_is_present(session, person, field):
                total += 1
        overall = round(100 * total / len(overall_fields))
    else:
        overall = 0

    next_field: dict[str, Any] = {}
    for field in sorted(fields, key=lambda f: (f.priority, f.key)):
        if not await field_is_present(session, person, field):
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
    }


def priority_name(p: Priority) -> str:
    return {"C": "critical", "I": "important", "E": "enrichment"}[p]


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
