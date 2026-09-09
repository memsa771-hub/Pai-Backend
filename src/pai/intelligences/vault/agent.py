from __future__ import annotations
from pai.platform.llm.gateway import LLMGateway
from pai.domains.memory.service import PersonMemoryService
from pai.kernel.contracts.schemas import VaultCandidate
from pai.intelligences.vault.service import VaultIntelligenceService
from pai.intelligences.vault.types import ExtractionBundle

class FactExtractionAgent:
    """Compatibility facade over VaultIntelligenceService (chat + document)."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.last_bundle: ExtractionBundle | None = None

    async def extract_from_chat(
        self,
        *,
        user_message: str,
        user_message_id: str,
        catalog_hint: str | None = None,
        known_facts: list[str] | None = None,
        person_id: str | None = None,
        memory: PersonMemoryService | None = None,
    ) -> list[VaultCandidate]:
        del catalog_hint  # catalog is owned by Vault Intelligence
        intel = VaultIntelligenceService(self._gateway, memory=memory)
        bundle = await intel.extract_chat_bundle(
            user_message=user_message,
            user_message_id=user_message_id,
            known_facts=known_facts,
            person_id=person_id,
        )
        self.last_bundle = bundle
        return bundle.candidates

    async def extract_from_document(
        self,
        *,
        document_id: str,
        document_text: str,
        document_type_hint: str = "generic",
        known_facts: list[str] | None = None,
        person_id: str | None = None,
        memory: PersonMemoryService | None = None,
    ) -> list[VaultCandidate]:
        intel = VaultIntelligenceService(self._gateway, memory=memory)
        candidates = await intel.extract_from_document(
            document_id=document_id,
            document_text=document_text,
            document_type_hint=document_type_hint,
            known_facts=known_facts,
            person_id=person_id,
        )
        return candidates


