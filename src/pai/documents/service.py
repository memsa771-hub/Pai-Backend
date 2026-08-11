from __future__ import annotations

import mimetypes
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings
from pai.core.errors import AuthError
from pai.documents.models import Document, DocumentCandidate, DocumentJob
from pai.ingestion.vault_apply import process_candidates
from pai.llm.gateway import LLMGateway
from pai.orchestration.agents import FactExtractionAgent
from pai.orchestration.schemas import VaultCandidate
from pai.person.models import Person
from pai.storage.supabase import SupabaseStorageProvider

ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "image/jpeg",
    "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".dll", ".js", ".msi"}


class DocumentNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__(code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404)


def validate_upload(filename: str, content_type: str, size: int, settings: Settings) -> None:
    lower = filename.lower()
    for ext in BLOCKED_EXTENSIONS:
        if lower.endswith(ext):
            raise AuthError(
                code="INVALID_FILE", message="File type not allowed.", status_code=400
            )
    if size > settings.document_max_bytes:
        raise AuthError(code="FILE_TOO_LARGE", message="File exceeds size limit.", status_code=413)
    if content_type not in ALLOWED_MIMES:
        guessed, _ = mimetypes.guess_type(filename)
        if (guessed or content_type) not in ALLOWED_MIMES:
            raise AuthError(
                code="INVALID_FILE", message="Unsupported MIME type.", status_code=400
            )


async def create_document_upload(
    session: AsyncSession,
    settings: Settings,
    person: Person,
    *,
    filename: str,
    content_type: str,
    data: bytes,
    storage: SupabaseStorageProvider,
) -> Document:
    validate_upload(filename, content_type, len(data), settings)
    doc_id = uuid.uuid4()
    path = f"{person.id}/{doc_id}/{filename}"
    await storage.upload_private(path, data, content_type)
    doc = Document(
        id=doc_id,
        person_id=person.id,
        storage_path=path,
        original_filename=filename,
        mime_type=content_type,
        size_bytes=len(data),
        status="uploaded",
    )
    session.add(doc)
    job = DocumentJob(
        document_id=doc.id,
        person_id=person.id,
        idempotency_key=f"extract-{doc.id}",
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(doc)
    return doc


async def enqueue_reprocess(session: AsyncSession, person_id: uuid.UUID, document_id: uuid.UUID) -> None:
    doc = await get_document_owned(session, person_id, document_id)
    job = DocumentJob(
        document_id=doc.id,
        person_id=person_id,
        idempotency_key=f"reprocess-{doc.id}-{uuid.uuid4()}",
        status="pending",
    )
    session.add(job)
    doc.status = "queued"
    await session.commit()


async def get_document_owned(
    session: AsyncSession, person_id: uuid.UUID, document_id: uuid.UUID
) -> Document:
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.person_id == person_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    return doc


def extract_text_from_bytes(data: bytes, mime_type: str, filename: str) -> str:
    if mime_type.startswith("text/"):
        return data.decode("utf-8", errors="replace")[:12000]
    return f"[binary document: {filename}, type {mime_type}]"[:12000]


async def process_document_job(
    session: AsyncSession,
    settings: Settings,
    job: DocumentJob,
    *,
    storage: SupabaseStorageProvider,
    gateway: LLMGateway,
) -> None:
    doc = await session.get(Document, job.document_id)
    if doc is None:
        job.status = "failed"
        job.last_error = "document missing"
        return
    doc.status = "processing"
    await session.flush()
    raw = await storage.download_bytes(doc.storage_path)
    text_content = extract_text_from_bytes(raw, doc.mime_type, doc.original_filename)
    fact_agent = FactExtractionAgent(gateway)
    orch_candidates = await fact_agent.extract_from_document(
        document_id=str(doc.id),
        document_text=text_content,
        document_type_hint=doc.document_type or "generic",
        person_id=str(doc.person_id),
    )
    doc.document_type = doc.document_type or "generic"
    person = await session.get(Person, doc.person_id)
    if person is None:
        job.status = "failed"
        return
    await session.execute(
        select(DocumentCandidate).where(DocumentCandidate.document_id == doc.id)
    )
    candidates_for_review: list[DocumentCandidate] = []
    for c in orch_candidates:
        c.source_type = "document"
        c.source_reference = str(doc.id)
        row = DocumentCandidate(
            document_id=doc.id,
            person_id=person.id,
            field_key=c.field_key,
            value=c.value if isinstance(c.value, dict) else c.value,
            confidence=c.confidence,
            evidence_text=c.evidence_text,
            review_status="pending",
            reasoning_summary=c.rationale_summary,
        )
        session.add(row)
        candidates_for_review.append(row)
    needs_review = any(
        c.confidence < 0.9 or c.requires_confirmation for c in orch_candidates
    )
    if needs_review:
        doc.status = "awaiting_review"
    else:
        await process_candidates(session, person, orch_candidates, from_document=True)
        doc.status = "processed"
    job.status = "completed"


async def claim_next_job(session: AsyncSession) -> DocumentJob | None:
    result = await session.execute(
        select(DocumentJob)
        .where(DocumentJob.status == "pending", DocumentJob.available_at <= datetime.now(UTC))
        .order_by(DocumentJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        await session.commit()
        return None
    job.status = "processing"
    job.locked_at = datetime.now(UTC)
    job.attempts += 1
    await session.commit()
    await session.refresh(job)
    return job


async def review_document_candidates(
    session: AsyncSession,
    person: Person,
    document_id: uuid.UUID,
    *,
    accept_ids: list[uuid.UUID],
) -> None:
    doc = await get_document_owned(session, person.id, document_id)
    result = await session.execute(
        select(DocumentCandidate).where(
            DocumentCandidate.document_id == doc.id,
            DocumentCandidate.person_id == person.id,
            DocumentCandidate.id.in_(accept_ids),
        )
    )
    to_apply: list[VaultCandidate] = []
    for row in result.scalars():
        row.review_status = "accepted"
        to_apply.append(
            VaultCandidate(
                field_key=row.field_key,
                value=row.value,
                confidence=row.confidence,
                evidence_text=row.evidence_text or "",
                source_type="document",
                source_reference=str(doc.id),
                rationale_summary=row.reasoning_summary or "",
            )
        )
    async with session.begin():
        await process_candidates(session, person, to_apply, from_document=True)
        doc.status = "processed"
    await session.commit()
