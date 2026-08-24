"""Read scans/photos with DeepSeek vision. Digital PDF/DOCX still use the native parser first."""

from __future__ import annotations

import base64
import io
import logging

import httpx

from pai.config import Settings
from pai.services.document_intelligence.digitization.schemas import DigitizationResult

logger = logging.getLogger(__name__)

_IMAGE_MIMES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}
_PROMPT = (
    "Transcribe this student document verbatim. Keep names, dates, numbers, GPA, "
    "scores, and table rows exactly as written. Do not invent missing fields. "
    "Return plain text only."
)


class DeepSeekVisionProvider:
    name = "deepseek_vision"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def configured(self) -> bool:
        return bool(self._settings.deepseek_api_key)

    async def digitize(self, data: bytes, *, mime_type: str, filename: str) -> DigitizationResult:
        _ = filename
        if not self.configured():
            return DigitizationResult(
                text="",
                method="unavailable",
                provider=self.name,
                quality="unreadable",
                needs_ocr=True,
            )
        images = _images_for_vision(
            data, mime_type, max_pages=self._settings.document_vision_max_pages
        )
        if not images:
            return DigitizationResult(
                text="",
                method="unavailable",
                provider=self.name,
                quality="unreadable",
                needs_ocr=True,
            )
        content: list[dict] = [{"type": "text", "text": _PROMPT}]
        for img_mime, blob in images:
            b64 = base64.b64encode(blob).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img_mime};base64,{b64}",
                        "detail": "high",
                    },
                }
            )
        model = self._settings.llm_document_vision_model
        timeout = max(
            self._settings.document_processing_timeout_seconds,
            self._settings.llm_timeout_seconds,
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 6000,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self._settings.deepseek_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.HTTPError:
            logger.warning("DeepSeek vision request failed")
            return DigitizationResult(
                text="",
                method="unavailable",
                provider=self.name,
                model=model,
                quality="unreadable",
                needs_ocr=True,
            )
        if response.status_code >= 400:
            logger.warning("DeepSeek vision error status=%s body=%s", response.status_code, response.text[:300])
            return DigitizationResult(
                text="",
                method="unavailable",
                provider=self.name,
                model=model,
                quality="unreadable",
                needs_ocr=True,
            )
        body = response.json()
        text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return DigitizationResult(
            text=text,
            method="vision",
            provider=self.name,
            model=model,
            page_count=len(images),
            quality="good" if len(text) >= 40 else "low",
            needs_ocr=False,
            raw_response={"model": model, "usage": body.get("usage") or {}, "pages": len(images), "text": text},
        )


def _images_for_vision(data: bytes, mime_type: str, *, max_pages: int) -> list[tuple[str, bytes]]:
    mime = (mime_type or "").split(";")[0].strip().lower()
    mapped = _IMAGE_MIMES.get(mime)
    if mapped:
        return [(mapped, data)]
    if mime == "application/pdf":
        return _pdf_embedded_images(data, max_pages=max_pages)
    return []


def _pdf_embedded_images(data: bytes, *, max_pages: int) -> list[tuple[str, bytes]]:
    """ponytail: scans are usually one JPEG per page. Rasterizing PDFs needs pypdfium2 later."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        return []
    out: list[tuple[str, bytes]] = []
    for page in reader.pages[: max(1, max_pages)]:
        try:
            images = page.images
        except Exception:
            continue
        for img in images:
            raw = getattr(img, "data", None)
            if not isinstance(raw, (bytes, bytearray)) or len(raw) < 8000:
                continue
            out.append((_sniff_image_mime(bytes(raw)), bytes(raw)))
            if len(out) >= max_pages:
                return out
    return out


def _sniff_image_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"
