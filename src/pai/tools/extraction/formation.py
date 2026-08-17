"""Separate extraction from memory selection.

Recall-first extractors may emit false positives, OTHER facts, negations,
hypotheticals, and third-party attributions. Only student-attributed,
non-hypothetical catalog facts are eligible for Vault writes. Everything
else is observed memory — additive evidence, not a Vault mutation.
"""

from __future__ import annotations

import json

from pai.orchestration.schemas import OBSERVED_FIELD_KEY, VaultCandidate

_STUDENT = frozenset({"", "student", "user", "self", "me"})
_VAULT_ASSERTIONS = frozenset({"explicit", "inferred"})
_EXPLICITNESS_TO_ASSERTION = {
    "explicit": "explicit",
    "strongly_implied": "inferred",
    "uncertain": "uncertain",
}
_CAUTION = {
    "explicit": 0,
    "inferred": 1,
    "uncertain": 2,
    "hypothetical": 3,
    "negated": 4,
}


def assertion_of(candidate: VaultCandidate) -> str:
    """Prefer the more cautious of assertion_status vs legacy explicitness."""
    status = candidate.assertion_status or "explicit"
    from_exp = _EXPLICITNESS_TO_ASSERTION.get(candidate.explicitness, "explicit")
    if _CAUTION.get(status, 0) >= _CAUTION.get(from_exp, 0):
        return status
    return from_exp


def is_vault_eligible(candidate: VaultCandidate) -> bool:
    if candidate.field_key == OBSERVED_FIELD_KEY:
        return False
    if (candidate.fact_type or "").strip().upper() == "OTHER_POTENTIAL_FACT":
        return False
    if assertion_of(candidate) not in _VAULT_ASSERTIONS:
        return False
    who = (candidate.attributed_to or "student").strip().lower()
    return who in _STUDENT


def partition_candidates(
    candidates: list[VaultCandidate],
) -> tuple[list[VaultCandidate], list[VaultCandidate]]:
    vault: list[VaultCandidate] = []
    observed: list[VaultCandidate] = []
    for row in candidates:
        (vault if is_vault_eligible(row) else observed).append(row)
    return vault, observed


def format_observed(candidate: VaultCandidate) -> str:
    status = assertion_of(candidate)
    who = (candidate.attributed_to or "student").strip() or "student"
    fact = (
        candidate.value
        if isinstance(candidate.value, str)
        else json.dumps(candidate.value, default=str)
    )
    kind = candidate.fact_type or candidate.field_key
    parts = [f"Observed ({status}, {kind}): {fact}"]
    if who.lower() not in _STUDENT:
        parts.append(f"attributed_to={who}")
    evidence = (candidate.evidence_text or "").strip()
    if evidence:
        parts.append(f'evidence="{evidence[:240]}"')
    return " ".join(parts)
