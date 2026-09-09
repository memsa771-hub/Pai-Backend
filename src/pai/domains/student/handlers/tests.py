from __future__ import annotations


from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.evidence import record_entity_evidence
from pai.domains.student.person.models import Person
from pai.domains.student.test_attempts import ENTITY_TYPE as TEST_ENTITY
from pai.domains.student.test_attempts import parse_test_observation, upsert_test_attempt
from pai.kernel.contracts.schemas import VaultCandidate

from pai.domains.student.handlers.common import _log_typed_history, _as_items

async def _apply_test_scores(
    session: AsyncSession,
    person: Person,
    candidate: VaultCandidate,
    *,
    verification_level: str,
) -> str:
    status = "rejected"
    for raw in _as_items(candidate.value):
        observation = parse_test_observation(raw)
        if observation is None:
            continue
        row, outcome = await upsert_test_attempt(session, person.id, observation)
        record_entity_evidence(
            session,
            entity_type=TEST_ENTITY,
            entity_id=row.id,
            attribute="overall_score",
            candidate=candidate,
            verification_level=verification_level,
        )
        await _log_typed_history(
            session,
            person,
            candidate.field_key,
            old_value=None,
            new_value={
                "testType": row.test_type,
                "attemptNumber": row.attempt_number,
                "overallScore": row.overall_score,
            },
            candidate=candidate,
            entity_type=TEST_ENTITY,
            entity_id=row.id,
        )
        if outcome == "accepted" or status == "rejected":
            status = outcome
    return status



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
    status = await _apply_test_scores(
        session, person, candidate, verification_level=verification_level
    )
    if recompute_completion and person.vault and status != "rejected":
        await apply_completion_to_vault(session, person, person.vault)
    out = "pending" if vault_status == "pending" and status != "rejected" else status
    return TypedApplyResult(candidate.field_key, out, candidate.confidence)

