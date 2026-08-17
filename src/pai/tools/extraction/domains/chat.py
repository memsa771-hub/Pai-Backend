from __future__ import annotations

from pai.tools.extraction.boosters import run_deterministic_boosters
from pai.tools.extraction.llm_extractor import OmnibusLLMExtractor
from pai.tools.extraction.merge import merge_candidates
from pai.tools.extraction.normalize import normalize_candidates
from pai.tools.extraction.types import ExtractionBundle, ExtractionRequest, SourceKind
from pai.services.journey.extract import extract_goal
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
        # Short explicit statements (city, GPA, marks) are already caught by boosters.
        # Skip the extract LLM so a simple chat turn is one counselor call, not two.
        words = len((request.text or "").split())
        llm_cands: list = []
        provider_calls = 0
        goal = None
        goalish = extract_goal(request.text or "") is not None
        if not (boosters and words <= 12 and not goalish):
            llm = OmnibusLLMExtractor(gateway)
            llm_cands = await llm.extract(request)
            provider_calls = 1
            goal = llm.last_goal
        merged = merge_candidates(boosters, llm_cands)
        normalized = normalize_candidates(merged)
        return ExtractionBundle(
            candidates=normalized,
            domains_fired=["deterministic"] + (["omnibus_llm"] if provider_calls else []),
            booster_hits=hits,
            coverage_notes=[
                "chat: deterministic boosters"
                + (" + multi-domain LLM pass" if provider_calls else " only"),
                f"candidates={len(normalized)}",
            ],
            provider_calls=provider_calls,
            source=SourceKind.CHAT,
            meta={"booster_count": len(boosters), "llm_count": len(llm_cands)},
            current_goal=goal,
        )
