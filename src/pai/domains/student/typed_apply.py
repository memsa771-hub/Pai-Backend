"""Schema storage dispatch; canonical entity merges live in small handlers."""
from __future__ import annotations
from pai.domains.student.handlers import education, identity, tests
from pai.domains.student.handlers.common import TypedApplyResult, _as_items, _log_typed_history, _parse_date
from pai.domains.student.handlers.education import (
    EDUCATION_ENTITY, _education_payload, _load_educations,
    _apply_qualification_identity, _contradiction_issue, _apply_education_fields,
    _education_snapshot, _ambiguity_issue, revalidate_education_timeline,
    _apply_education_one,
)
from pai.domains.student.handlers.skills import _upsert_skills
from pai.domains.student.handlers.work import _upsert_work
from pai.domains.student.handlers.projects import _upsert_projects
from pai.domains.student.handlers.certifications import _upsert_certs
from pai.domains.student.handlers.identity import _person_value
from pai.domains.student.handlers.tests import _apply_test_scores
from pai.domains.student.vault.completion import apply_completion_to_vault
from pai.domains.student.evidence import DEFAULT_VERIFICATION


def collection_handler(upsert):
    async def apply(session, person, candidate, field, *, vault_status,
                    recompute_completion=True, verification_level=DEFAULT_VERIFICATION):
        status = await upsert(session, person, _as_items(candidate.value), candidate)
        if recompute_completion and person.vault and status != "rejected":
            await apply_completion_to_vault(session, person, person.vault)
        return TypedApplyResult(candidate.field_key, status, candidate.confidence)
    return apply


HANDLERS = {
    "educations": education.apply,
    "test_attempts": tests.apply,
    "person": identity.apply,
    "skills": collection_handler(_upsert_skills),
    "work_experiences": collection_handler(_upsert_work),
    "projects": collection_handler(_upsert_projects),
    "certifications": collection_handler(_upsert_certs),
}


async def apply_typed_candidate(session, person, candidate, field, *, vault_status,
                                recompute_completion=True, verification_level=DEFAULT_VERIFICATION):
    if vault_status == "pending":
        from pai.kernel.evidence.vault_apply import apply_vault_candidate
        result = await apply_vault_candidate(
            session, person, candidate, vault_status="pending",
            verification_level=verification_level, recompute_completion=recompute_completion,
        )
        return TypedApplyResult(result.field_key, result.status, result.confidence)
    handler = HANDLERS.get(field.storage)
    if handler is None or (field.storage == "person" and not field.person_column):
        return TypedApplyResult(candidate.field_key, "rejected", candidate.confidence)
    return await handler(session, person, candidate, field, vault_status=vault_status,
                         recompute_completion=recompute_completion, verification_level=verification_level)
