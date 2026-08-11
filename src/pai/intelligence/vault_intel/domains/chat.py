from __future__ import annotations

from pai.intelligence.vault_intel.boosters import run_deterministic_boosters
from pai.intelligence.vault_intel.llm_extractor import OmnibusLLMExtractor
from pai.intelligence.vault_intel.merge import merge_candidates
from pai.intelligence.vault_intel.normalize import normalize_candidates
from pai.intelligence.vault_intel.types import ExtractionBundle, ExtractionRequest, SourceKind
from pai.llm.gateway import LLMGateway


class ChatSourceDomain:
    """Extract Vault facts from a student chat message."""

    kind = SourceKind.CHAT.value

    async def extract(
        self, request: ExtractionRequest, *, gateway: LLMGateway
    ) -> ExtractionBundle:
        boosters, hits = run_deterministic_boosters(
            request.text,
            source_reference=request.source_reference,
            source_type="chat",
        )
        llm = OmnibusLLMExtractor(gateway)
        llm_cands = await llm.extract(request)
        merged = merge_candidates(boosters, llm_cands)
        normalized = normalize_candidates(merged)
        return ExtractionBundle(
            candidates=normalized,
            domains_fired=["deterministic", "omnibus_llm"],
            booster_hits=hits,
            coverage_notes=[
                "chat: deterministic boosters + multi-domain LLM pass",
                f"candidates={len(normalized)}",
            ],
            provider_calls=1,
            source=SourceKind.CHAT,
            meta={"booster_count": len(boosters), "llm_count": len(llm_cands)},
        )
