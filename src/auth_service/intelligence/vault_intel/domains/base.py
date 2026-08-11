from __future__ import annotations

from typing import Protocol

from auth_service.intelligence.vault_intel.types import ExtractionBundle, ExtractionRequest
from auth_service.llm.gateway import LLMGateway


class SourceDomain(Protocol):
    """Pluggable extraction subdomain (chat, document, linkedin, …)."""

    kind: str

    async def extract(
        self, request: ExtractionRequest, *, gateway: LLMGateway
    ) -> ExtractionBundle: ...
