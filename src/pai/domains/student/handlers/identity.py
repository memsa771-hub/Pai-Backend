from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from pai.domains.student.person.models import Person
from pai.kernel.contracts.schemas import VaultCandidate
from pai.domains.student.handlers.common import _log_typed_history

from typing import Any


from pai.domains.student.normalization.phone import normalize_phone


def _person_value(field_key: str, value: Any) -> Any:
    if field_key == "identity.phone" and isinstance(value, str):
        try:
            return normalize_phone(value)
        except ValueError:
            return value.strip()
    if field_key in {"identity.full_name", "identity.preferred_name"} and isinstance(value, str):
        return value.strip()[:256]
    return value



from pai.domains.student.evidence import DEFAULT_VERIFICATION
from pai.domains.student.vault.catalog import CatalogField
from pai.domains.student.vault.completion import apply_completion_to_vault
from pai.domains.student.handlers.common import TypedApplyResult

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
    value = _person_value(candidate.field_key, candidate.value)
    old = getattr(person, field.person_column, None)
    setattr(person, field.person_column, value)
    await _log_typed_history(
        session,
        person,
        candidate.field_key,
        old_value=old,
        new_value=value,
        candidate=candidate,
    )
    if recompute_completion and person.vault:
        await apply_completion_to_vault(session, person, person.vault)
    out = "pending" if vault_status == "pending" else "accepted"
    return TypedApplyResult(candidate.field_key, out, candidate.confidence)

