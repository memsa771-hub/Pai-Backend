from __future__ import annotations

from pai.services.document_intelligence.config import policy, taxonomy


def known_types() -> set[str]:
    return set(taxonomy()["types"])


def default_type() -> str:
    return str(taxonomy().get("default_type") or "other")


def type_meta(document_type: str) -> dict:
    types = taxonomy()["types"]
    return dict(types.get(document_type) or types[default_type()])


def classify_from_name(filename: str, hint: str | None = None, text: str = "") -> str:
    from_text = _best_type(text)
    if from_text:
        return from_text
    if hint and hint in known_types() and hint != default_type():
        return hint
    return _best_type(filename) or default_type()


def _best_type(blob: str) -> str | None:
    text = (blob or "").lower()
    if not text:
        return None
    best_type = None
    best_len = 0
    for rule in taxonomy()["filename_hints"]:
        hit = max((len(token) for token in rule["needles"] if token and token in text), default=0)
        if hit > best_len:
            best_len = hit
            best_type = rule["type"]
    return best_type


def evidence_eligible(*, source_type: str, document_type: str) -> bool:
    rules = policy()
    if source_type in set(rules.get("generated_sources") or []):
        return False
    blocked = set(taxonomy().get("generated_types") or []) | set(rules.get("evidence_ineligible_types") or [])
    return document_type not in blocked


def normalize_source_type(value: str | None, *, default: str = "document_vault") -> str:
    allowed = set(taxonomy()["source_types"])
    return value if value in allowed else default


def normalize_created_by(value: str | None, *, default: str = "student") -> str:
    allowed = set(taxonomy()["created_by"])
    return value if value in allowed else default
