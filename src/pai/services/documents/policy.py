"""Compatibility wrappers over Document Intelligence taxonomy."""

from __future__ import annotations

from pai.services.document_intelligence.classification.taxonomy import (
    classify_from_name,
    evidence_eligible,
    known_types,
    normalize_created_by,
    normalize_source_type,
)
from pai.services.document_intelligence.config import taxonomy

DOCUMENT_TYPES = known_types()
SOURCE_TYPES = frozenset(taxonomy()["source_types"])
CREATED_BY = frozenset(taxonomy()["created_by"])
EXTRACTABLE_MIMES = set(taxonomy()["native_parse_mimes"])


def classify_document_type(filename: str, hint: str | None = None) -> str:
    return classify_from_name(filename, hint)


def vault_extraction_policy(source_type: str) -> str:
    return "extract" if evidence_eligible(source_type=source_type, document_type="other") else "disabled"
