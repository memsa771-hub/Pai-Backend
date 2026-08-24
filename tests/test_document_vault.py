"""Document Vault: provenance, versions, attachments, review reject."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import delete, func, select

from pai.core.errors import AuthError
from pai.services.conversations.models import Conversation, Message
from pai.services.documents.models import Document, DocumentCandidate, DocumentJob
from pai.services.documents.policy import classify_document_type, vault_extraction_policy
from pai.services.documents.service import (
    attach_documents_to_message,
    attachment_note_for_message,
    create_document_upload,
    enqueue_reprocess,
    list_document_candidates,
    review_document_candidates,
)
from pai.services.person.models import Person


async def _delete_person(session, person: Person) -> None:
    await session.execute(delete(Person).where(Person.id == person.id))
    await session.commit()


def test_classify_resume_from_filename():
    assert classify_document_type("Musawir-CV-2027.pdf") == "resume"
    assert classify_document_type("official-transcript.pdf") == "transcript"
    assert classify_document_type("ielts-trf.pdf") == "ielts"
    assert classify_document_type("notes.pdf") == "other"
    assert classify_document_type("file.pdf", "sop") == "sop"


def test_ai_generated_never_auto_writes_vault():
    assert vault_extraction_policy("ai_generated") == "disabled"
    assert vault_extraction_policy("onboarding") == "extract"
    assert vault_extraction_policy("chat_attachment") == "extract"


class _FakeStorage:
    async def upload_private(self, path, data, mime):
        return path


def test_ai_generated_upload_skips_extract_job(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _run():
        async with factory() as session:
            person = Person(
                auth_provider="supabase",
                external_auth_id=f"vault-{uuid.uuid4()}",
                email=f"vault-{uuid.uuid4()}@example.com",
            )
            session.add(person)
            await session.flush()
            try:
                doc = await create_document_upload(
                    session,
                    postgres_ready,
                    person,
                    filename="sop-tum.txt",
                    content_type="text/plain",
                    data=b"Generated statement of purpose with enough characters.",
                    storage=_FakeStorage(),
                    source_type="ai_generated",
                    document_type="sop",
                    created_by="pai",
                )
                assert doc.vault_extraction_policy == "disabled"
                assert doc.status == "ready"
                assert doc.source_type == "ai_generated"
                assert doc.created_by == "pai"
                assert doc.current_version_id is not None
                jobs = await session.execute(
                    select(func.count())
                    .select_from(DocumentJob)
                    .where(DocumentJob.document_id == doc.id)
                )
                assert jobs.scalar_one() == 0
                try:
                    await enqueue_reprocess(session, person.id, doc.id)
                except AuthError as exc:
                    assert exc.code == "EXTRACTION_DISABLED"
                else:
                    raise AssertionError("ai_generated docs must not reprocess into the vault")
            finally:
                await _delete_person(session, person)

    asyncio.run(_run())


def test_chat_attachment_links_vault_document(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _run():
        async with factory() as session:
            person = Person(
                auth_provider="supabase",
                external_auth_id=f"attach-{uuid.uuid4()}",
                email=f"attach-{uuid.uuid4()}@example.com",
            )
            session.add(person)
            await session.flush()
            doc = Document(
                person_id=person.id,
                title="Transcript",
                document_type="transcript",
                source_type="chat_attachment",
                storage_path=f"{person.id}/transcript.pdf",
                original_filename="transcript.pdf",
                mime_type="application/pdf",
                size_bytes=12,
                status="ready",
            )
            conv = Conversation(person_id=person.id, status="active")
            session.add(doc)
            session.add(conv)
            await session.flush()
            msg = Message(
                conversation_id=conv.id,
                person_id=person.id,
                role="user",
                content="Can you check whether this transcript is enough for TUM?",
            )
            session.add(msg)
            await session.commit()
            try:
                linked = await attach_documents_to_message(
                    session, person.id, msg.id, [doc.id]
                )
                assert linked[0].id == doc.id
                note = await attachment_note_for_message(session, msg.id)
                assert "transcript.pdf" in note
                assert "transcript" in note
            finally:
                await _delete_person(session, person)

    asyncio.run(_run())


def test_review_can_reject_candidates(postgres_ready):
    from pai.data.db import get_session_factory, reset_engine_for_tests

    reset_engine_for_tests()
    factory = get_session_factory(postgres_ready)

    async def _run():
        async with factory() as session:
            person = Person(
                auth_provider="supabase",
                external_auth_id=f"review-{uuid.uuid4()}",
                email=f"review-{uuid.uuid4()}@example.com",
            )
            session.add(person)
            await session.flush()
            doc = Document(
                person_id=person.id,
                title="CV",
                document_type="resume",
                source_type="document_vault",
                storage_path=f"{person.id}/cv.pdf",
                original_filename="cv.pdf",
                mime_type="application/pdf",
                size_bytes=20,
                status="awaiting_review",
            )
            session.add(doc)
            await session.flush()
            cand = DocumentCandidate(
                document_id=doc.id,
                person_id=person.id,
                field_key="identity.full_name",
                value="Ada Lovelace",
                confidence=0.9,
                evidence_text="Name: Ada Lovelace",
                review_status="pending",
                reasoning_summary="printed on the CV",
            )
            session.add(cand)
            await session.commit()
            try:
                await review_document_candidates(
                    session, person, doc.id, accept_ids=[], reject_ids=[cand.id]
                )
                items = await list_document_candidates(session, person, doc.id)
                assert items[0]["reviewStatus"] == "rejected"
                assert items[0]["value"] == "Ada Lovelace"
                assert items[0]["evidenceText"] == "Name: Ada Lovelace"
                assert items[0]["reason"] == "printed on the CV"
            finally:
                await _delete_person(session, person)

    asyncio.run(_run())
