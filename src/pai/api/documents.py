from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.dependencies import get_db, resolve_person_from_token
from pai.documents.models import DocumentCandidate
from pai.documents.service import (
    create_document_upload,
    enqueue_reprocess,
    get_document_owned,
    review_document_candidates,
)
from pai.schemas import success
from pai.storage.supabase import SupabaseStorageProvider

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentReviewRequest(BaseModel):
    acceptCandidateIds: list[str]


def _storage(settings: Settings) -> SupabaseStorageProvider:
    return SupabaseStorageProvider(settings)


@router.post("")
async def upload_document(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(resolve_person_from_token),
    file: UploadFile = File(...),
) -> JSONResponse:
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
        )
    finally:
        await storage.aclose()
    return JSONResponse(
        status_code=202,
        content=success({"documentId": str(doc.id), "status": doc.status}),
    )


@router.get("")
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    from pai.documents.models import Document

    result = await session.execute(
        select(Document).where(Document.person_id == person.id).order_by(Document.created_at.desc())
    )
    items = [
        {
            "id": str(d.id),
            "filename": d.original_filename,
            "status": d.status,
            "documentType": d.document_type,
        }
        for d in result.scalars()
    ]
    return JSONResponse(content=success({"items": items}))


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    doc = await get_document_owned(session, person.id, document_id)
    storage = _storage(settings)
    try:
        signed = await storage.create_signed_download_url(
            doc.storage_path, person_id=person.id, expires_seconds=900
        )
    finally:
        await storage.aclose()
    return JSONResponse(
        content=success(
            {
                "id": str(doc.id),
                "filename": doc.original_filename,
                "status": doc.status,
                "documentType": doc.document_type,
                "downloadUrl": signed,
            }
        )
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    doc = await get_document_owned(session, person.id, document_id)
    storage = _storage(settings)
    try:
        await storage.delete_object(doc.storage_path)
    finally:
        await storage.aclose()
    await session.delete(doc)
    await session.commit()
    return JSONResponse(content=success({"message": "Document deleted."}))


@router.get("/{document_id}/status")
async def document_status(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    doc = await get_document_owned(session, person.id, document_id)
    return JSONResponse(content=success({"status": doc.status, "documentType": doc.document_type}))


@router.get("/{document_id}/candidates")
async def document_candidates(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    await get_document_owned(session, person.id, document_id)
    result = await session.execute(
        select(DocumentCandidate).where(
            DocumentCandidate.document_id == document_id,
            DocumentCandidate.person_id == person.id,
        )
    )
    items = [
        {
            "id": str(c.id),
            "fieldKey": c.field_key,
            "confidence": c.confidence,
            "reviewStatus": c.review_status,
        }
        for c in result.scalars()
    ]
    return JSONResponse(content=success({"candidates": items}))


@router.post("/{document_id}/review")
async def review_document(
    document_id: uuid.UUID,
    body: DocumentReviewRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    ids = [uuid.UUID(x) for x in body.acceptCandidateIds]
    await review_document_candidates(session, person, document_id, accept_ids=ids)
    return JSONResponse(content=success({"message": "Review applied."}))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    await enqueue_reprocess(session, person.id, document_id)
    return JSONResponse(content=success({"message": "Reprocess queued."}))
