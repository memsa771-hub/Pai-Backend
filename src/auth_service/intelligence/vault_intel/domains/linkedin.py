from __future__ import annotations

from auth_service.core.errors import AuthError
from auth_service.intelligence.vault_intel.types import ExtractionBundle, ExtractionRequest, SourceKind
from auth_service.llm.gateway import LLMGateway


class LinkedInSourceDomain:
    """Future: import public LinkedIn profile / résumé export into Vault."""

    kind = SourceKind.LINKEDIN.value

    async def extract(
        self, request: ExtractionRequest, *, gateway: LLMGateway
    ) -> ExtractionBundle:
        raise AuthError(
            code="SOURCE_NOT_ENABLED",
            message=(
                "LinkedIn Vault Intelligence is registered but not enabled yet. "
                "Chat and document sources are available now."
            ),
            status_code=501,
        )
