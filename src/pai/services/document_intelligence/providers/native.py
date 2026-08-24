from __future__ import annotations

from pai.services.document_intelligence.config import taxonomy
from pai.services.document_intelligence.digitization.schemas import DigitizationResult
from pai.services.documents.text import extract_text_from_bytes


class NativeDocumentProvider:
    name = "native"

    def configured(self) -> bool:
        return True

    async def digitize(self, data: bytes, *, mime_type: str, filename: str) -> DigitizationResult:
        mime = (mime_type or "").split(";")[0].strip().lower()
        text = extract_text_from_bytes(data, mime, filename)
        native_mimes = set(taxonomy()["native_parse_mimes"])
        if mime not in native_mimes:
            return DigitizationResult(
                text="",
                method="unavailable",
                provider=self.name,
                quality="unreadable",
                needs_ocr=True,
            )
        quality = "good" if len(text.strip()) >= 40 else "unreadable"
        return DigitizationResult(
            text=text,
            method="native_text",
            provider=self.name,
            page_count=max(text.count("\f") + 1, 1),
            quality=quality,
            needs_ocr=quality == "unreadable" and mime == "application/pdf",
        )
