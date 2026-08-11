from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.config import Settings
from auth_service.core.errors import AuthError
from auth_service.conversations.models import Message
from auth_service.conversations.service import save_assistant_message, start_orchestration_run
from auth_service.orchestration.orchestrator import PAIOrchestrator
from auth_service.person.models import Person
from auth_service.vault.completion import compute_completion


async def handle_user_message(
    session: AsyncSession,
    settings: Settings,
    person: Person,
    conversation_id: uuid.UUID,
    user_message: Message,
    *,
    orchestrator: PAIOrchestrator | None = None,
) -> dict:
    if person.vault is None:
        raise AuthError(
            code="VAULT_NOT_READY",
            message="Person vault not initialized. Call bootstrap first.",
            status_code=400,
        )
    orch = orchestrator or PAIOrchestrator(settings)
    run = await start_orchestration_run(
        session, person, conversation_id=conversation_id, run_type="chat_message"
    )
    try:
        graph_state = await orch.run_chat_turn(
            session, person, conversation_id, user_message, run=run
        )
    except AuthError:
        raise
    except Exception as exc:
        run.status = "failed"
        run.error_code = "LLM_ERROR"
        from datetime import UTC, datetime

        run.completed_at = datetime.now(UTC)
        await session.commit()
        from auth_service.llm.providers.deepseek import LLMProviderError

        if isinstance(exc, LLMProviderError):
            raise exc
        raise AuthError(
            code="ORCHESTRATION_FAILED",
            message="Counselor request failed.",
            status_code=502,
        ) from exc
    await session.commit()
    reply = graph_state.get("assistant_reply") or ""
    assistant = await save_assistant_message(
        session,
        person,
        conversation_id,
        reply,
        provider=settings.llm_default_provider,
        model=settings.llm_counseling_model,
    )
    completion = await compute_completion(session, person, person.vault)
    conv_result = graph_state.get("assistant_result")
    next_q = None
    if conv_result and hasattr(conv_result, "next_question"):
        next_q = conv_result.next_question
    elif isinstance(conv_result, dict):
        next_q = conv_result.get("next_question")
    return {
        "messageId": str(assistant.id),
        "reply": reply,
        "vaultUpdates": [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in (graph_state.get("applied_vault_changes") or [])
        ],
        "pendingConfirmations": [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in (graph_state.get("pending_confirmations") or [])
        ],
        "taskResults": [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in (graph_state.get("task_results") or [])
        ],
        "vaultCompletion": {
            "critical": completion.get("critical", 0),
            "important": completion.get("important", 0),
            "enrichment": completion.get("enrichment", 0),
        },
        "nextQuestion": next_q,
    }
