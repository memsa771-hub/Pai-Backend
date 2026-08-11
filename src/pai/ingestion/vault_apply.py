from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import get_settings
from pai.orchestration.schemas import VaultCandidate
from pai.orchestration.verifier import (
    policy_decision,
    validate_candidate,
    verification_level_for,
)
from pai.ingestion.typed_apply import apply_typed_candidate
from pai.person.models import Person, VaultEvidence, VaultHistory, VaultValue
from pai.vault.catalog import get_catalog_field
from pai.vault.completion import apply_completion_to_vault
from pai.vault.security import SensitiveValueCodec


class VaultApplyResult(BaseModel):
    field_key: str
    status: str
    confidence: float


async def apply_vault_candidate(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    *,
    vault_status: str,
    verification_level: str,
    recompute_completion: bool = True,
) -> VaultApplyResult:
    from pai.core.errors import UnknownFieldError

    field = get_catalog_field(candidate.field_key)
    if field is None or person.vault is None:
        raise UnknownFieldError()
    settings = get_settings()
    codec = SensitiveValueCodec(settings.vault_encryption_key)
    vault = person.vault
    result = await session.execute(
        select(VaultValue).where(
            VaultValue.vault_id == vault.id,
            VaultValue.field_key == candidate.field_key,
            VaultValue.status == "active",
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.value == candidate.value and vault_status == "active":
        session.add(
            VaultEvidence(
                vault_value_id=existing.id,
                source_type=candidate.source_type,
                source_reference=candidate.source_reference,
                evidence_text=candidate.evidence_text,
                confidence=candidate.confidence,
            )
        )
        return VaultApplyResult(
            field_key=candidate.field_key, status="reinforced", confidence=candidate.confidence
        )
    old_val = existing.value if existing else None
    if existing:
        existing.status = "superseded"
    status = "pending_confirmation" if vault_status == "pending" else "active"
    row = VaultValue(
        vault_id=vault.id,
        field_key=candidate.field_key,
        value=None if field.sensitive else candidate.value,
        value_encrypted=codec.encrypt_json(candidate.value) if field.sensitive else None,
        status=status,
        verification_level=verification_level,
        confidence=candidate.confidence,
        supersedes_id=existing.id if existing else None,
    )
    session.add(row)
    await session.flush()
    session.add(
        VaultEvidence(
            vault_value_id=row.id,
            source_type=candidate.source_type,
            source_reference=candidate.source_reference,
            evidence_text=candidate.evidence_text,
            confidence=candidate.confidence,
        )
    )
    session.add(
        VaultHistory(
            vault_id=vault.id,
            field_key=candidate.field_key,
            action="updated" if old_val is not None else "created",
            old_value=old_val,
            new_value=candidate.value,
            actor_type="system",
            actor_id=str(person.id),
            reason=candidate.rationale_summary,
        )
    )
    if recompute_completion and person.vault is not None:
        await apply_completion_to_vault(session, person, person.vault)
    out_status = "pending" if status == "pending_confirmation" else "accepted"
    return VaultApplyResult(
        field_key=candidate.field_key, status=out_status, confidence=candidate.confidence
    )


async def process_candidates(
    session: AsyncSession,
    person: Person,
    candidates: list[VaultCandidate],
    *,
    from_document: bool = False,
) -> tuple[list[VaultApplyResult], list[VaultCandidate]]:
    accepted: list[VaultApplyResult] = []
    pending: list[VaultCandidate] = []
    mutated = False
    for raw in candidates:
        candidate = validate_candidate(raw)
        if candidate is None:
            continue
        field = get_catalog_field(candidate.field_key)
        if field is None:
            continue
        decision = policy_decision(candidate)
        if decision == "reject":
            continue
        vlevel = verification_level_for(
            candidate, accepted=(decision == "accept"), from_document=from_document
        )
        vault_status = "pending" if decision == "pending" else "active"
        if decision == "pending":
            pending.append(candidate)

        if field.storage == "vault_value":
            if vault_status == "pending":
                await apply_vault_candidate(
                    session,
                    person,
                    candidate,
                    vault_status="pending",
                    verification_level=vlevel,
                    recompute_completion=False,
                )
                accepted.append(
                    VaultApplyResult(
                        field_key=candidate.field_key,
                        status="pending",
                        confidence=candidate.confidence,
                    )
                )
            else:
                accepted.append(
                    await apply_vault_candidate(
                        session,
                        person,
                        candidate,
                        vault_status="active",
                        verification_level=vlevel,
                        recompute_completion=False,
                    )
                )
            mutated = True
            continue

        typed = await apply_typed_candidate(
            session,
            person,
            candidate,
            field,
            vault_status=vault_status,
            recompute_completion=False,
        )
        if typed.status != "rejected":
            accepted.append(
                VaultApplyResult(
                    field_key=typed.field_key,
                    status=typed.status,
                    confidence=typed.confidence,
                )
            )
            mutated = True
    if mutated and person.vault is not None:
        await apply_completion_to_vault(session, person, person.vault)
    return accepted, pending
