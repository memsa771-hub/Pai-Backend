from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.dependencies import get_db, require_onboarding_complete
from pai.intelligences.documents.config import taxonomy as load_taxonomy
from pai.intelligences.documents.verification.service import (
    list_open_cases,
    public_case,
    resolve_case,
)
from pai.domains.documents.models import DocumentJob
from pai.domains.documents.service import (
    _public_document,
    create_document_upload,
    delete_document,
    enqueue_reprocess,
    get_document_owned,
    list_document_candidates,
    list_documents,
    review_document_candidates,
)
from pai.schemas import success
from pai.platform.storage.supabase import SupabaseStorageProvider

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentReviewRequest(BaseModel):
    acceptCandidateIds: list[uuid.UUID] = Field(default_factory=list)
    rejectCandidateIds: list[uuid.UUID] = Field(default_factory=list)


class VerificationResolveRequest(BaseModel):
    resolutionType: str
    notes: str | None = None


def _storage(settings: Settings) -> SupabaseStorageProvider:
    return SupabaseStorageProvider(settings)


@router.post("")
async def upload_document(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
    file: UploadFile = File(...),
    document_type: str | None = Form(default=None, alias="documentType"),
    source_type: str | None = Form(default="document_vault", alias="sourceType"),
) -> JSONResponse:
    allowed_sources = set(load_taxonomy()["source_types"]) - {"ai_generated"}
    if source_type not in allowed_sources:
        source_type = "document_vault"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    storage = _storage(settings)
    try:
        doc = await create_document_upload(
            session,
            settings,
            person,
            filename=file.filename or "upload.bin",
            content_type=content_type,
            data=data,
            storage=storage,
            source_type=source_type or "document_vault",
            document_type=document_type,
            created_by="student",
        )
    finally:
        await storage.aclose()
    return JSONResponse(status_code=202, content=success(_public_document(doc)))


@router.get("/taxonomy")
async def document_taxonomy(person=Depends(require_onboarding_complete)) -> JSONResponse:
    _ = person
    tax = load_taxonomy()
    return JSONResponse(content=success({"categories": tax["categories"], "types": tax["types"]}))


@router.get("/verification-cases")
async def verification_cases_api(
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    rows = await list_open_cases(session, person.id)
    return JSONResponse(content=success({"items": [public_case(row) for row in rows]}))


@router.post("/verification-cases/{case_id}/resolve")
async def resolve_verification_case_api(
    case_id: uuid.UUID,
    body: VerificationResolveRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    row = await resolve_case(
        session, person, case_id, resolution_type=body.resolutionType, notes=body.notes
    )
    return JSONResponse(content=success(public_case(row)))


@router.get("")
async def list_documents_api(
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    items = await list_documents(session, person.id)
    return JSONResponse(content=success({"items": [_public_document(d) for d in items]}))


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    doc = await get_document_owned(session, person.id, document_id)
    storage = _storage(settings)
    try:
        signed = await storage.create_signed_download_url(
            doc.storage_path, person_id=person.id, expires_seconds=900
        )
    finally:
        await storage.aclose()
    payload = _public_document(doc)
    payload["downloadUrl"] = signed
    return JSONResponse(content=success(payload))


@router.delete("/{document_id}")
async def delete_document_api(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    storage = _storage(settings)
    try:
        await delete_document(session, person, document_id, storage)
    finally:
        await storage.aclose()
    return JSONResponse(content=success({"message": "Document deleted."}))


@router.get("/{document_id}/status")
async def document_status(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    doc = await get_document_owned(session, person.id, document_id)
    job = await session.scalar(
        select(DocumentJob)
        .where(DocumentJob.document_id == doc.id)
        .order_by(DocumentJob.created_at.desc())
        .limit(1)
    )
    return JSONResponse(
        content=success(
            {
                "status": doc.status,
                "processingStatus": doc.status,
                "documentType": doc.document_type,
                "category": doc.category,
                "sourceType": doc.source_type,
                "verificationStatus": doc.verification_status,
                "lifecycleStatus": doc.lifecycle_status,
                "identityStatus": doc.identity_status,
                "attentionState": _public_document(doc)["attentionState"],
                "vaultExtractionPolicy": doc.vault_extraction_policy,
                "currentStage": job.current_stage if job else None,
                "jobStatus": job.status if job else None,
                "lastError": job.last_error if job else None,
            }
        )
    )


@router.get("/{document_id}/candidates")
async def document_candidates(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    items = await list_document_candidates(session, person, document_id)
    return JSONResponse(content=success({"candidates": items}))


@router.post("/{document_id}/review")
async def review_document(
    document_id: uuid.UUID,
    body: DocumentReviewRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    await review_document_candidates(
        session,
        person,
        document_id,
        accept_ids=body.acceptCandidateIds,
        reject_ids=body.rejectCandidateIds,
    )
    return JSONResponse(content=success({"message": "Review applied."}))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    await enqueue_reprocess(session, person.id, document_id)
    return JSONResponse(content=success({"message": "Reprocess queued."}))
