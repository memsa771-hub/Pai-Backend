from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings
from pai.core.errors import AuthError
from pai.services.documents.models import (
    Document,
    DocumentCandidate,
    DocumentJob,
    DocumentVersion,
    MessageDocument,
)
from pai.services.document_intelligence.classification.classifier import classify_document
from pai.services.document_intelligence.classification.taxonomy import (
    evidence_eligible,
    normalize_created_by,
    normalize_source_type,
)
from pai.services.document_intelligence.evidence.attention import attention_state, journey_criticality
from pai.services.document_intelligence.security.scanner import scan_bytes
from pai.services.document_intelligence.security.validation import validate_upload_bytes
from pai.ingestion.vault_apply import process_candidates
from pai.services.document_intelligence.verification.service import close_open_cases_for_fields
from pai.services.jobs.lease import reclaim_expired_leases
from pai.llm.gateway import LLMGateway
from pai.orchestration.schemas import VaultCandidate
from pai.services.person.models import Person, PersonVault, VaultValue
from pai.storage.supabase import SupabaseStorageProvider
from pai.services.documents.relations import add_relation
_DOC_JOB_LOCK_NS = 87423092
_CLAIM_SQL = """
SELECT c.id
FROM document_jobs AS c
WHERE c.status = 'pending'
  AND c.available_at <= :now
  AND NOT EXISTS (
      SELECT 1
      FROM document_jobs AS p
      WHERE p.document_id = c.document_id
        AND p.status = 'processing'
  )
  AND pg_try_advisory_xact_lock(:lock_ns, hashtext(c.document_id::text))
ORDER BY c.created_at
FOR UPDATE SKIP LOCKED
LIMIT 1
"""


class DocumentNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__(code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404)


class DocumentIdentityUnresolvedError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_IDENTITY_UNRESOLVED",
            message="Resolve whether this document belongs to you before accepting extracted facts.",
            status_code=409,
        )


def _public_document(doc: Document, *, open_cases: int = 0) -> dict:
    attention = attention_state(doc, open_cases=open_cases)
    return {
        "id": str(doc.id),
        "title": doc.title or doc.original_filename,
        "filename": doc.original_filename,
        "documentType": doc.document_type or "other",
        "category": doc.category,
        "sourceType": doc.source_type,
        "createdBy": doc.created_by,
        "processingStatus": doc.status,
        "status": doc.status,
        "verificationStatus": doc.verification_status,
        "lifecycleStatus": doc.lifecycle_status,
        "trustLevel": doc.trust_level,
        "identityStatus": doc.identity_status,
        "authenticityStatus": doc.authenticity_status,
        "baseCriticality": doc.base_criticality,
        "journeyCriticality": journey_criticality(doc, attention=attention),
        "attentionState": attention,
        "evidenceEligible": doc.evidence_eligible,
        "sizeBytes": doc.size_bytes,
        "mimeType": doc.mime_type,
        "currentVersionId": str(doc.current_version_id) if doc.current_version_id else None,
        "vaultExtractionPolicy": doc.vault_extraction_policy,
        "createdAt": doc.created_at.isoformat() if doc.created_at else None,
        "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
    }


async def create_document_upload(
    session: AsyncSession,
    settings: Settings,
    person: Person,
    *,
    filename: str,
    content_type: str,
    data: bytes,
    storage: SupabaseStorageProvider,
    source_type: str = "document_vault",
    document_type: str | None = None,
    created_by: str = "student",
    title: str | None = None,
) -> Document:
    mime = validate_upload_bytes(filename, content_type, data, settings)
    await scan_bytes(data, filename=filename, settings=settings)
    source = normalize_source_type(source_type)
    actor = normalize_created_by(created_by)
    classified = classify_document(filename=filename, hint=document_type, source_type=source)
    eligible = evidence_eligible(source_type=source, document_type=classified["document_type"])
    policy = "extract" if eligible else "disabled"
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()
    path = f"{person.id}/{doc_id}/{version_id}/{filename}"
    await storage.upload_private(path, data, mime)
    digest = hashlib.sha256(data).hexdigest()
    doc = Document(
        id=doc_id,
        person_id=person.id,
        title=(title or filename)[:256],
        document_type=classified["document_type"],
        category=classified["category"],
        source_type=source,
        created_by=actor,
        base_criticality=classified["base_criticality"],
        evidence_eligible=eligible,
        vault_extraction_policy=policy,
        trust_level=classified["trust_level"],
        storage_path=path,
        original_filename=filename,
        mime_type=mime,
        size_bytes=len(data),
        status="uploaded",
        lifecycle_status="draft" if source == "ai_generated" else "active",
    )
    session.add(doc)
    await session.flush()
    version = DocumentVersion(
        id=version_id,
        document_id=doc.id,
        version_number=1,
        storage_path=path,
        original_filename=filename,
        mime_type=mime,
        size_bytes=len(data),
        sha256=digest,
        created_by=actor,
    )
    session.add(version)
    await session.flush()
    doc.current_version_id = version.id
    session.add(
        DocumentJob(
            document_id=doc.id,
            document_version_id=version.id,
            person_id=person.id,
            idempotency_key=f"extract-{version.id}",
            status="pending",
        )
    )
    await session.commit()
    await session.refresh(doc)
    return doc


async def enqueue_reprocess(session: AsyncSession, person_id: uuid.UUID, document_id: uuid.UUID) -> None:
    doc = await get_document_owned(session, person_id, document_id)
    job = DocumentJob(
        document_id=doc.id,
        document_version_id=doc.current_version_id,
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
        select(Document).where(
            Document.id == document_id,
            Document.person_id == person_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    return doc


async def list_documents(session: AsyncSession, person_id: uuid.UUID) -> list[Document]:
    result = await session.execute(
        select(Document)
        .where(Document.person_id == person_id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def attach_documents_to_message(
    session: AsyncSession,
    person_id: uuid.UUID,
    message_id: uuid.UUID,
    document_ids: list[uuid.UUID],
) -> list[Document]:
    if not document_ids:
        return []
    unique = list(dict.fromkeys(document_ids))
    result = await session.execute(
        select(Document).where(
            Document.person_id == person_id,
            Document.deleted_at.is_(None),
            Document.id.in_(unique),
        )
    )
    docs = list(result.scalars().all())
    if len(docs) != len(unique):
        raise DocumentNotFoundError()
    by_id = {row.id: row for row in docs}
    for doc_id in unique:
        doc = by_id[doc_id]
        session.add(
            MessageDocument(
                message_id=message_id,
                document_id=doc.id,
                document_version_id=doc.current_version_id,
            )
        )
        add_relation(
            session,
            document_id=doc.id,
            version_id=doc.current_version_id,
            relation_type="attached_to",
            related_type="message",
            related_id=str(message_id),
        )
    await session.commit()
    return [by_id[doc_id] for doc_id in unique]


async def attachment_note_for_message(session: AsyncSession, message_id: uuid.UUID) -> str:
    result = await session.execute(
        select(Document)
        .join(MessageDocument, MessageDocument.document_id == Document.id)
        .where(MessageDocument.message_id == message_id, Document.deleted_at.is_(None))
    )
    rows = list(result.scalars().all())
    if not rows:
        return ""
    names = [f"{d.original_filename} ({d.document_type or 'other'})" for d in rows]
    return "Attached documents: " + ", ".join(names)


async def _current_vault_values(
    session: AsyncSession, person: Person, field_keys: list[str]
) -> dict[str, object]:
    if not field_keys:
        return {}
    vault_id = await session.scalar(
        select(PersonVault.id).where(PersonVault.person_id == person.id)
    )
    if vault_id is None:
        return {}
    result = await session.execute(
        select(VaultValue.field_key, VaultValue.value).where(
            VaultValue.vault_id == vault_id,
            VaultValue.field_key.in_(field_keys),
            VaultValue.status.in_(("active", "pending_confirmation")),
        )
    )
    return {key: value for key, value in result.all()}


async def process_document_job(
    session: AsyncSession,
    settings: Settings,
    job: DocumentJob,
    *,
    storage: SupabaseStorageProvider,
    gateway: LLMGateway,
) -> None:
    from pai.services.document_intelligence.pipeline import run_document_analysis

    await run_document_analysis(session, settings, job, storage=storage, gateway=gateway)


async def claim_next_job(session: AsyncSession) -> DocumentJob | None:
    await reclaim_expired_leases(session, DocumentJob)
    now = datetime.now(UTC)
    result = await session.execute(
        text(_CLAIM_SQL),
        {"now": now, "lock_ns": _DOC_JOB_LOCK_NS},
    )
    job_id = result.scalar_one_or_none()
    if job_id is None:
        await session.commit()
        return None
    job = await session.get(DocumentJob, job_id)
    if job is None:
        await session.commit()
        return None
    job.status = "processing"
    job.locked_at = now
    job.attempts += 1
    await session.commit()
    await session.refresh(job)
    return job


async def list_document_candidates(
    session: AsyncSession, person: Person, document_id: uuid.UUID
) -> list[dict]:
    doc = await get_document_owned(session, person.id, document_id)
    result = await session.execute(
        select(DocumentCandidate)
        .where(
            DocumentCandidate.document_id == doc.id,
            DocumentCandidate.person_id == person.id,
        )
        .order_by(DocumentCandidate.created_at.desc())
    )
    rows = list(result.scalars().all())
    current = await _current_vault_values(session, person, [row.field_key for row in rows])
    return [
        {
            "id": str(row.id),
            "fieldKey": row.field_key,
            "value": row.value,
            "evidenceText": row.evidence_text,
            "confidence": row.confidence,
            "reviewStatus": row.review_status,
            "reason": row.reasoning_summary,
            "currentVaultValue": current.get(row.field_key),
            "documentVersionId": str(row.document_version_id) if row.document_version_id else None,
            "documentJobId": str(row.document_job_id) if row.document_job_id else None,
        }
        for row in rows
    ]


async def review_document_candidates(
    session: AsyncSession,
    person: Person,
    document_id: uuid.UUID,
    *,
    accept_ids: list[uuid.UUID],
    reject_ids: list[uuid.UUID] | None = None,
) -> None:
    doc = await get_document_owned(session, person.id, document_id)
    reject_ids = reject_ids or []
    requested = list(dict.fromkeys([*accept_ids, *reject_ids]))
    if requested:
        found = await session.scalars(
            select(DocumentCandidate.id).where(
                DocumentCandidate.document_id == doc.id,
                DocumentCandidate.person_id == person.id,
                DocumentCandidate.id.in_(requested),
            )
        )
        if not list(found.all()):
            raise AuthError(
                code="CANDIDATE_NOT_FOUND",
                message="Those ids are not candidates for this document. Copy ids from GET /documents/{id}/candidates.",
                status_code=400,
            )
    if accept_ids and doc.identity_status == "mismatch":
        raise DocumentIdentityUnresolvedError()
    if reject_ids:
        result = await session.execute(
            select(DocumentCandidate).where(
                DocumentCandidate.document_id == doc.id,
                DocumentCandidate.person_id == person.id,
                DocumentCandidate.id.in_(reject_ids),
            )
        )
        for row in result.scalars():
            row.review_status = "rejected"
    to_apply: list[VaultCandidate] = []
    if accept_ids:
        result = await session.execute(
            select(DocumentCandidate).where(
                DocumentCandidate.document_id == doc.id,
                DocumentCandidate.person_id == person.id,
                DocumentCandidate.id.in_(accept_ids),
            )
        )
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
    if to_apply:
        await process_candidates(session, person, to_apply, from_document=True, already_reconciled=True)
        await close_open_cases_for_fields(
            session,
            person_id=person.id,
            document_id=doc.id,
            field_keys={row.field_key for row in to_apply},
        )
    leftover = await session.execute(
        select(DocumentCandidate.id).where(
            DocumentCandidate.document_id == doc.id,
            DocumentCandidate.review_status == "pending",
        )
    )
    doc.status = "awaiting_review" if leftover.first() is not None else "processed"
    await session.commit()


async def delete_document(
    session: AsyncSession,
    person: Person,
    document_id: uuid.UUID,
    storage: SupabaseStorageProvider,
) -> None:
    doc = await get_document_owned(session, person.id, document_id)
    versions = await session.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
    )
    paths = {doc.storage_path}
    paths.update(row.storage_path for row in versions.scalars())
    for path in paths:
        await storage.delete_object(path)
    doc.deleted_at = datetime.now(UTC)
    doc.status = "deleted"
    await session.commit()
