from __future__ import annotations

from auth_service.core.errors import AuthError
from auth_service.intelligence.vault_intel.types import ExtractionBundle, ExtractionRequest, SourceKind
from auth_service.llm.gateway import LLMGateway


class SocialSourceDomain:
    """Future: social / third-party profile signals into Vault."""

    kind = SourceKind.SOCIAL.value

    async def extract(
        self, request: ExtractionRequest, *, gateway: LLMGateway
    ) -> ExtractionBundle:
        raise AuthError(
            code="SOURCE_NOT_ENABLED",
            message=(
                "Social Vault Intelligence is registered but not enabled yet. "
                "Chat and document sources are available now."
            ),
            status_code=501,
        )
