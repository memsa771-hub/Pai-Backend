from __future__ import annotations

from pydantic import BaseModel

from pai.llm.gateway import LLMGateway
from pai.llm.schemas import LLMMessage
from pai.orchestration.agents import FactExtractionAgent
from pai.orchestration.schemas import VaultCandidate
from pai.services.document_intelligence.classification.taxonomy import type_meta
from pai.services.document_intelligence.config import policy
from pai.services.document_intelligence.evidence.grounding import evidence_grounded
from pai.services.document_intelligence.extraction.schemas import degree as degree_schema
from pai.services.document_intelligence.extraction.schemas import passport as passport_schema
from pai.services.document_intelligence.extraction.schemas import resume as resume_schema
from pai.services.document_intelligence.extraction.schemas import test_score as test_schema
from pai.services.document_intelligence.extraction.schemas import transcript as transcript_schema

# Schema modules stay in code; which type uses which schema lives in taxonomy.json.
_SCHEMAS: dict[str, tuple[type[BaseModel], object]] = {
    "passport": (passport_schema.PassportExtraction, passport_schema.to_field_map),
    "transcript": (transcript_schema.TranscriptExtraction, transcript_schema.to_field_map),
    "degree": (degree_schema.DegreeExtraction, degree_schema.to_field_map),
    "resume": (resume_schema.ResumeExtraction, resume_schema.to_field_map),
    "test_score": (test_schema.TestScoreExtraction, test_schema.to_field_map),
}


async def extract_candidates(
    *,
    gateway: LLMGateway,
    document_id: str,
    document_text: str,
    document_type: str,
    known_facts: list[str],
    person_id: str,
) -> list[VaultCandidate]:
    typed = await _try_typed(
        gateway,
        document_text=document_text,
        document_type=document_type,
        document_id=document_id,
    )
    if typed:
        return typed
    agent = FactExtractionAgent(gateway)
    fallback = await agent.extract_from_document(
        document_id=document_id,
        document_text=document_text,
        document_type_hint=document_type,
        known_facts=known_facts,
        person_id=person_id,
    )
    return [row for row in fallback if evidence_grounded(row.evidence_text, document_text)]


async def _try_typed(
    gateway: LLMGateway,
    *,
    document_text: str,
    document_type: str,
    document_id: str,
) -> list[VaultCandidate]:
    spec = _SCHEMAS.get(str(type_meta(document_type).get("extractor") or ""))
    if spec is None:
        return []
    schema, mapper = spec
    rules = policy()
    limit = int(rules.get("extract_char_limit") or 20000)
    try:
        out = await gateway.run(
            task="document_extract",
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "Extract only fields present in the document. "
                        "evidence_text must be a verbatim span. Do not invent facts."
                    ),
                ),
                LLMMessage(role="user", content=document_text[:limit]),
            ],
            output_schema=schema,
            temperature=0.0,
        )
    except Exception:
        return []
    if not isinstance(out, BaseModel):
        return []
    base = float(rules.get("typed_confidence") or 0.9)
    candidates: list[VaultCandidate] = []
    for field_key, value, evidence in mapper(out):
        if not evidence or not evidence_grounded(evidence, document_text):
            continue
        candidates.append(
            VaultCandidate(
                field_key=field_key,
                value=value,
                confidence=base,
                evidence_text=evidence,
                source_type="document",
                source_reference=document_id,
            )
        )
    return candidates
