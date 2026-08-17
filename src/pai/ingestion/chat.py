from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings
from pai.core.errors import AuthError
from pai.conversations.models import Message
from pai.conversations.service import save_assistant_message, start_orchestration_run
from pai.llm.gateway import LLMGateway
from pai.orchestration.context import chat_stay_payload
from pai.orchestration.orchestrator import PAIOrchestrator
from pai.person.models import Person


async def handle_user_message(
    session: AsyncSession,
    settings: Settings,
    person: Person,
    conversation_id: uuid.UUID,
    user_message: Message,
    *,
    orchestrator: PAIOrchestrator | None = None,
    gateway: LLMGateway | None = None,
) -> dict:
    if person.vault is None:
        raise AuthError(
            code="VAULT_NOT_READY",
            message="Person vault not initialized. Call bootstrap first.",
            status_code=400,
        )
    orch = orchestrator or PAIOrchestrator(settings, gateway=gateway)
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
        from pai.llm.providers.deepseek import LLMProviderError

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
    vault_updates = [
        c.model_dump() if hasattr(c, "model_dump") else c
        for c in (graph_state.get("applied_vault_changes") or [])
    ]
    pending = [
        p.model_dump() if hasattr(p, "model_dump") else p
        for p in (graph_state.get("pending_confirmations") or [])
    ]
    task_results = [
        t.model_dump() if hasattr(t, "model_dump") else t
        for t in (graph_state.get("task_results") or [])
        if (getattr(t, "status", None) if not isinstance(t, dict) else t.get("status"))
        not in ("rejected", "duplicate")
    ]
    tool_trace = list(graph_state.get("tool_trace") or [])
    result = graph_state.get("assistant_result")
    next_question = None
    suggested = None
    if result is not None:
        if isinstance(result, dict):
            next_question = result.get("next_question")
            suggested = result.get("suggested_next_step")
        else:
            next_question = getattr(result, "next_question", None)
            suggested = getattr(result, "suggested_next_step", None)
    stay = chat_stay_payload(
        graph_state.get("student_context"),
        next_question=next_question,
        suggested_next_step=suggested,
    )
    return {
        "conversationId": str(conversation_id),
        "messageId": str(assistant.id),
        "reply": reply,
        "vaultUpdates": vault_updates,
        "pendingConfirmations": pending,
        "taskResults": task_results,
        "toolTrace": tool_trace,
        **stay,
    }
