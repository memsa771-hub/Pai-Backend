"""Convert grounded Vault outcomes to independent Memory observations."""
from __future__ import annotations
import hashlib
import json
import re
from pai.domains.student.vault.catalog import get_catalog_field
from pai.kernel.contracts.schemas import VaultCandidate
from pai.kernel.evidence.assertion import assertion_of, format_observed, is_vault_eligible
from pai.domains.memory.formation import MemoryDraft, merge_drafts, _link_turn

def memory_key_for(candidate: VaultCandidate) -> str:
    if is_vault_eligible(candidate):
        catalog = get_catalog_field(candidate.field_key)
        if catalog and catalog.repeatable:
            body = json.dumps(candidate.value, sort_keys=True, ensure_ascii=False, default=str)
            return f"semantic:{candidate.field_key}:" + hashlib.sha256(body.encode()).hexdigest()[:24]
        return f"semantic:{candidate.field_key}"
    who = (candidate.attributed_to or "student").strip().lower() or "student"
    body = candidate.value
    if not isinstance(body, str):
        body = json.dumps(body, sort_keys=True, default=str)
    kind = candidate.fact_type or candidate.field_key or "fact"
    return f"observed:{who}:{_slug(str(kind))}:{_slug(str(body))}"



def importance_of(candidate: VaultCandidate) -> float:
    # Contextual importance is supplied by semantic extraction, never field names.
    return candidate.contextual_importance if candidate.contextual_importance is not None else 0.5



def drafts_from_turn(
    *,
    accepted: list[VaultCandidate] | None = None,
    pending: list[VaultCandidate] | None = None,
    conflicts: list[VaultCandidate] | None = None,
    observed: list[VaultCandidate] | None = None,
) -> list[MemoryDraft]:
    drafts: list[MemoryDraft] = []
    for row in accepted or []:
        draft = _draft_from_candidate(row, status="active", kind=_kind_for(row))
        if draft is not None:
            drafts.append(draft)
    for row in pending or []:
        draft = _draft_from_candidate(row, status="candidate", kind=_kind_for(row), key_prefix="pending")
        if draft is not None:
            drafts.append(draft)
    for row in conflicts or []:
        draft = _draft_from_candidate(
            row, status="candidate", kind="observed", key_prefix="claim"
        )
        if draft is not None:
            drafts.append(draft)
    for row in observed or []:
        draft = _draft_from_candidate(row, status=_observed_status(row), kind="observed")
        if draft is not None:
            drafts.append(draft)
    return _link_turn(merge_drafts(drafts))



def _draft_from_candidate(
    candidate: VaultCandidate,
    *,
    status: str,
    kind: str,
    key_prefix: str | None = None,
) -> MemoryDraft | None:
    field = get_catalog_field(candidate.field_key)
    if field is not None and field.sensitive:
        return None
    importance = importance_of(candidate)
    if importance < 0.15:
        return None
    key = memory_key_for(candidate)
    if key_prefix:
        key = f"{key_prefix}:{candidate.field_key}:{_slug(str(candidate.value)[:40])}"
    return MemoryDraft(
        memory_key=key,
        content=_content_for(candidate),
        kind=kind,
        status=status if importance >= 0.15 else "ephemeral",
        confidence=float(candidate.confidence),
        importance=importance,
        assertion_status=assertion_of(candidate),
        evidence=(candidate.evidence_text or "")[:400],
        source_references=[candidate.source_reference] if candidate.source_reference else [],
        belongs_to=_belongs_to(candidate.field_key),
        field_key=candidate.field_key,
        value=candidate.value,
    )



def _kind_for(candidate: VaultCandidate) -> str:
    if candidate.is_correction:
        return "decision"
    return "semantic"



def _observed_status(candidate: VaultCandidate) -> str:
    if candidate.temporal_status in ("future", "unknown"):
        return "candidate"
    status = assertion_of(candidate)
    if status in ("hypothetical", "uncertain"):
        return "candidate"
    if status == "inferred":
        return "candidate"
    return "active"



def _belongs_to(field_key: str | None) -> str:
    key = field_key or ""
    if key.startswith(("application.", "finance.", "mobility.")):
        return "goal:now"
    return "profile"



def _content_for(candidate: VaultCandidate) -> str:
    if not is_vault_eligible(candidate):
        return format_observed(candidate)
    value = candidate.value
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    status = assertion_of(candidate)
    label = candidate.field_key
    if status == "negated":
        return f"Rejected {label}: {value}"
    if status == "hypothetical":
        return f"Considering {label}: {value} (conditional)"
    if candidate.is_correction:
        return f"Updated {label}: {value}"
    return f"{label}: {value}"



def _slug(text: str, n: int = 48) -> str:
    import unicodedata
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    token = "".join(ch if ch.isalnum() else "_" for ch in normalized).strip("_")
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return (token[:n] or "fact") + ":" + digest

