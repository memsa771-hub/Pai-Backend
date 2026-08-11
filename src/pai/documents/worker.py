from __future__ import annotations

import asyncio
import logging

from pai.config import Settings, get_settings
from pai.data.db import get_session_factory
from pai.documents.models import DocumentJob
from pai.documents.service import claim_next_job, process_document_job
from pai.llm.gateway import LLMGateway
from pai.storage.supabase import SupabaseStorageProvider

logger = logging.getLogger(__name__)


async def run_document_worker_once(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    factory = get_session_factory(settings)
    storage = SupabaseStorageProvider(settings)
    gateway = LLMGateway(settings)
    async with factory() as session:
        job = await claim_next_job(session)
        if job is None:
            return False
        try:
            await process_document_job(session, settings, job, storage=storage, gateway=gateway)
            await session.commit()
        except Exception as exc:
            logger.exception("Document job failed")
            await session.rollback()
            job = await session.get(DocumentJob, job.id)
            if job:
                job.status = "pending" if job.attempts < 3 else "failed"
                job.last_error = str(exc)[:500]
                await session.commit()
    return True


async def document_worker_loop(settings: Settings, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            processed = await run_document_worker_once(settings)
            if not processed:
                await asyncio.sleep(2.0)
        except OSError as exc:
            # Transient DNS / network blips to Supabase pooler (common on Windows).
            logger.warning("Document worker DB unreachable (%s); retrying…", exc)
            await asyncio.sleep(15.0)
        except Exception as exc:
            msg = str(exc).lower()
            if "getaddrinfo" in msg or "connect" in msg or "timeout" in msg:
                logger.warning("Document worker connection issue (%s); retrying…", exc)
                await asyncio.sleep(15.0)
            else:
                logger.exception("Document worker iteration error")
                await asyncio.sleep(5.0)
