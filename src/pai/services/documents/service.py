from __future__ import annotations

import mimetypes
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings
from pai.core.errors import AuthError
from pai.services.documents.models import Document, DocumentCandidate, DocumentJob
from pai.services.documents.text import extract_text_from_bytes
from pai.ingestion.vault_apply import process_candidates
from pai.services.memory.formation import apply_memory_drafts, drafts_from_turn
from pai.tools.extraction.formation import partition_candidates
from pai.llm.gateway import LLMGateway
from pai.orchestration.agents import FactExtractionAgent
from pai.orchestration.schemas import VaultCandidate
from pai.services.person.models import Person
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


def _fail_job(job: DocumentJob, doc: Document | None, message: str) -> None:
    job.status = "failed"
    job.last_error = message[:500]
    if doc is not None:
        doc.status = "failed"


async def _known_facts_for(session: AsyncSession, person: Person) -> list[str]:
    from pai.orchestration.context import build_known_facts
    from pai.services.person.profile_snapshot import load_typed_profile_records
    from pai.services.vault.service import VaultService

    sparse: dict = {}
    if person.vault is not None:
        unified = await VaultService().get_unified_vault(
            session, person, include_sensitive=False
        )
        sparse = unified.get("sparseFields") or {}
    typed = await load_typed_profile_records(session, person.id)
    return build_known_facts(
        identity={"preferredName": person.preferred_name, "fullName": person.full_name},
        sparse=sparse,
        typed=typed,
    )


async def process_document_job(
    session: AsyncSession,
    settings: Settings,
    job: DocumentJob,
    *,
    storage: SupabaseStorageProvider,
    gateway: LLMGateway,
) -> None:
    _ = settings
    doc = await session.get(Document, job.document_id)
    if doc is None:
        job.status = "failed"
        job.last_error = "document missing"
        return
    person = await session.get(Person, doc.person_id)
    if person is None:
        _fail_job(job, doc, "person missing")
        return
    doc.status = "processing"
    await session.flush()
    raw = await storage.download_bytes(doc.storage_path)
    text_content = extract_text_from_bytes(raw, doc.mime_type, doc.original_filename)
    if len(text_content.strip()) < 40:
        _fail_job(
            job,
            doc,
            "Could not read text from this file. Upload a text-based PDF or DOCX, not a scan.",
        )
        return
    hint = doc.document_type or "generic"
    known = await _known_facts_for(session, person)
    fact_agent = FactExtractionAgent(gateway)
    orch_candidates = await fact_agent.extract_from_document(
        document_id=str(doc.id),
        document_text=text_content,
        document_type_hint=hint,
        known_facts=known,
        person_id=str(doc.person_id),
    )
    doc.document_type = hint
    applied_keys: set[str] = set()
    vault_cands, observed = partition_candidates(orch_candidates)
    pending_cands: list[VaultCandidate] = []
    if vault_cands:
        accepted, pending_cands = await process_candidates(
            session, person, vault_cands, from_document=True
        )
        applied_keys = {row.field_key for row in accepted if row.status != "pending"}
    accepted_cands = [c for c in vault_cands if c.field_key in applied_keys]
    drafts = drafts_from_turn(
        accepted=accepted_cands,
        pending=pending_cands,
        observed=observed,
    )
    if drafts:
        await apply_memory_drafts(session, person.id, drafts)
    for c in orch_candidates:
        c.source_type = "document"
        c.source_reference = str(doc.id)
        session.add(
            DocumentCandidate(
                document_id=doc.id,
                person_id=person.id,
                field_key=c.field_key,
                value=c.value if isinstance(c.value, dict) else c.value,
                confidence=c.confidence,
                evidence_text=c.evidence_text,
                review_status="accepted" if c.field_key in applied_keys else "pending",
                reasoning_summary=c.rationale_summary,
            )
        )
    pending_left = any(c.field_key not in applied_keys for c in orch_candidates)
    doc.status = "awaiting_review" if pending_left else "processed"
    job.status = "completed"
    from pai.services.journey.service import record_document_processed

    record_document_processed(
        session,
        person.id,
        document_id=doc.id,
        filename=doc.original_filename or "file",
    )


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
