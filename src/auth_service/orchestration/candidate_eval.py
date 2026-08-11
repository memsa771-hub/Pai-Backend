from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.orchestration.schemas import CandidateResult, VaultCandidate
from auth_service.orchestration.verifier import policy_decision, validate_candidate
from auth_service.person.models import Person, VaultValue
from auth_service.vault.catalog import get_catalog_field


def _normalize(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip().lower()


async def evaluate_candidate_with_context(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
) -> CandidateResult:
    validated = validate_candidate(candidate)
    if validated is None:
        return CandidateResult(
            candidate=candidate,
            outcome="reject",
            rationale_summary="Failed schema or catalog validation",
        )
    field = get_catalog_field(candidate.field_key)
    assert field is not None
    existing_val: Any = None
    if field.storage == "vault_value" and person.vault is not None:
        row = await session.execute(
            select(VaultValue.value, VaultValue.value_encrypted, VaultValue.status).where(
                VaultValue.vault_id == person.vault.id,
                VaultValue.field_key == candidate.field_key,
                VaultValue.status == "active",
            )
        )
        hit = row.first()
        if hit is not None:
            existing_val = hit.value
    elif field.storage == "vault_value":
        existing_val = None
    else:
        from auth_service.config import get_settings
        from auth_service.vault.service import VaultService

        svc = VaultService(get_settings())
        unified = await svc.get_unified_vault(session, person, include_sensitive=False)
        sparse = unified.get("sparseFields") or {}
        if candidate.field_key in sparse:
            existing_val = sparse[candidate.field_key]

    if existing_val is not None and _normalize(existing_val) == _normalize(candidate.value):
        return CandidateResult(
            candidate=candidate,
            outcome="reinforce",
            rationale_summary="Same normalized value already active",
        )
    if existing_val is not None and _normalize(existing_val) != _normalize(candidate.value):
        if candidate.is_correction and candidate.explicitness == "explicit":
            pass
        else:
            return CandidateResult(
                candidate=candidate,
                outcome="conflict",
                rationale_summary="Different active value exists",
            )

    if candidate.requires_confirmation or field.sensitive:
        if candidate.explicitness == "explicit" and not field.sensitive:
            decision = policy_decision(validated)
        else:
            return CandidateResult(
                candidate=candidate,
                outcome="pending_confirmation",
                rationale_summary="Sensitive or requires confirmation",
            )
    else:
        decision = policy_decision(validated)

    if decision == "reject":
        return CandidateResult(
            candidate=candidate,
            outcome="reject",
            rationale_summary="Policy rejected candidate",
        )
    if decision == "pending":
        return CandidateResult(
            candidate=candidate,
            outcome="pending_confirmation",
            rationale_summary="Pending confirmation per policy",
        )
    return CandidateResult(
        candidate=candidate,
        outcome="accept",
        rationale_summary="Explicit valid non-sensitive fact",
    )
