"""Map aliases / messy keys onto the official Vault catalog."""

from __future__ import annotations

from typing import Any

from auth_service.orchestration.schemas import VaultCandidate
from auth_service.vault.catalog import VAULT_CATALOG, get_catalog_field

_ALIASES: dict[str, str] = {
    "education.degree": "education.program",
    "education.qualification": "education.program",
    "education.cgpa": "education.gpa",
    "education.percentage": "education.marks",
    "education.group": "education.stream",
    "application.destination": "application.study_country",
    "application.country": "application.study_country",
    "application.target_country": "application.study_country",
    "application.goal": "application.career_interest",
    "application.program_interest": "application.career_interest",
    "career.goal": "application.career_interest",
    "location.city": "location.current_city",
    "identity.name": "identity.full_name",
    "finance.budget": "finance.funding_status",
    "mobility.countries": "mobility.preferred_regions",
}


def normalize_candidate(candidate: VaultCandidate) -> VaultCandidate | None:
    key = (candidate.field_key or "").strip()
    key = _ALIASES.get(key, key)
    key = _ALIASES.get(key.lower(), key) if key.lower() in _ALIASES else key
    # case-insensitive catalog match
    if key not in VAULT_CATALOG:
        lowered = {k.lower(): k for k in VAULT_CATALOG}
        key = lowered.get(key.lower(), key)
    field = get_catalog_field(key)
    if field is None or field.derived or not field.editable:
        return None
    candidate.field_key = key
    candidate.value = _normalize_value(key, candidate.value)
    if candidate.confidence > 1.0:
        candidate.confidence = 1.0
    if candidate.confidence < 0.0:
        candidate.confidence = 0.0
    return candidate


def _normalize_value(field_key: str, value: Any) -> Any:
    if field_key == "education.gpa" and isinstance(value, (int, float)):
        return {"gpa": float(value), "gpa_scale": 4.0}
    if field_key == "education.marks":
        if isinstance(value, str) and "/" in value:
            parts = value.split("/", 1)
            try:
                return {"obtained": float(parts[0].strip()), "total": float(parts[1].strip())}
            except ValueError:
                return value
        if isinstance(value, dict):
            obtained = value.get("obtained") or value.get("marks_obtained")
            total = value.get("total") or value.get("marks_total")
            if obtained is not None and total is not None:
                return {"obtained": float(obtained), "total": float(total)}
        return value
    if field_key == "application.target_universities":
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value
    if field_key == "mobility.preferred_regions":
        if isinstance(value, str):
            return [v.strip() for v in value.replace(" and ", ",").split(",") if v.strip()]
        return value
    if field_key == "education.additional_maths" and isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1")
    if field_key == "finance.scholarship_interest" and isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1")
    return value


def normalize_candidates(candidates: list[VaultCandidate]) -> list[VaultCandidate]:
    out: list[VaultCandidate] = []
    for c in candidates:
        norm = normalize_candidate(c)
        if norm is not None:
            out.append(norm)
    return out
