from __future__ import annotations

from pai.config import Settings
from pai.services.document_intelligence.providers.base import DocumentOCRProvider
from pai.services.document_intelligence.providers.deepseek_vision import DeepSeekVisionProvider
from pai.services.document_intelligence.providers.native import NativeDocumentProvider


def ocr_provider(settings: Settings) -> DocumentOCRProvider:
    name = (settings.document_ocr_provider or "deepseek_vision").strip().lower()
    if name in ("native", "none", "off"):
        return NativeDocumentProvider()
    return DeepSeekVisionProvider(settings)
