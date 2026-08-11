from __future__ import annotations

from pai.intelligence.vault_intel.boosters import run_deterministic_boosters
from pai.intelligence.vault_intel.llm_extractor import OmnibusLLMExtractor
from pai.intelligence.vault_intel.merge import merge_candidates
from pai.intelligence.vault_intel.normalize import normalize_candidates
from pai.intelligence.vault_intel.types import ExtractionBundle, ExtractionRequest, SourceKind
from pai.llm.gateway import LLMGateway


class DocumentSourceDomain:
    """Extract Vault facts from uploaded document text (CV, transcript, …)."""

    kind = SourceKind.DOCUMENT.value

    async def extract(
        self, request: ExtractionRequest, *, gateway: LLMGateway
    ) -> ExtractionBundle:
        # Documents: truncate for LLM but run boosters on a larger window
        text = request.text or ""
        booster_text = text[:50000]
        llm_text = text[:14000]
        boosters, hits = run_deterministic_boosters(
            booster_text,
            source_reference=request.source_reference,
            source_type="document",
        )
        llm_req = request.model_copy(update={"text": llm_text})
        llm = OmnibusLLMExtractor(gateway)
        llm_cands = await llm.extract(llm_req)
        merged = merge_candidates(boosters, llm_cands)
        normalized = normalize_candidates(merged)
        return ExtractionBundle(
            candidates=normalized,
            domains_fired=["deterministic", "omnibus_llm", "document"],
            booster_hits=hits,
            coverage_notes=[
                f"document:{request.document_type_hint or 'generic'}",
                f"candidates={len(normalized)}",
            ],
            provider_calls=1,
            source=SourceKind.DOCUMENT,
            meta={"chars": len(text)},
        )
