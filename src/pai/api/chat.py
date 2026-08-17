from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.conversations import service as conv_svc
from pai.dependencies import get_db, require_onboarding_complete
from pai.ingestion.chat import handle_user_message
from pai.schemas import ApiErrorResponse, success

chat_router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    """One counselor turn for this student. Always continues the same PAI thread."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"message": "I want MS CS in Germany under 20000 EUR"}]
        }
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=16000,
        description="Student message to PAI.",
        examples=["I want MS CS in Germany under 20000 EUR"],
    )


_AUTH_ERRORS = {
    401: {"model": ApiErrorResponse, "description": "Missing/invalid Bearer token"},
    403: {"model": ApiErrorResponse, "description": "Onboarding not completed"},
    422: {"model": ApiErrorResponse, "description": "Validation error"},
    502: {"model": ApiErrorResponse, "description": "LLM / orchestration failure"},
}


def _message_item(m) -> dict:
    return {
        "id": str(m.id),
        "role": m.role,
        "content": m.content,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
    }


@chat_router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    summary="Send a counselor message",
    description=(
        "Primary PAI turn. Requires `Authorization: Bearer <accessToken>`.\n\n"
        "PAI is **one counselor per student**. Every message continues the same "
        "thread. An empty transcript opens with a Vault-grounded greeting.\n\n"
        "Each turn reconstructs knowledge from the Person Vault, typed profile, "
        "semantic memory, and (when configured) Tavily web search.\n\n"
        "**Swagger:** Authorize with `data.accessToken` only (no `Bearer` prefix)."
    ),
    responses=_AUTH_ERRORS,
)
async def chat(
    body: ChatRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    conv = await conv_svc.get_or_create_person_conversation(
        session, person, settings=settings
    )
    await conv_svc.ensure_thread_opening(session, person, conv.id, settings=settings)
    user_msg = await conv_svc.save_user_message(session, person, conv.id, body.message)
    gateway = getattr(request.app.state, "llm_gateway", None)
    data = await handle_user_message(
        session, settings, person, conv.id, user_msg, gateway=gateway
    )
    return JSONResponse(content=success(data))


@chat_router.get(
    "/chat/messages",
    summary="Load the counselor transcript",
    description=(
        "The one PAI history for this student. Omit `offset` to get the latest "
        "`limit` messages (chat window). Pass `offset=0` to read from the start."
    ),
    responses=_AUTH_ERRORS,
)
async def get_chat_messages(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
    limit: int = Query(50, ge=1, le=100),
    offset: int | None = Query(
        None,
        ge=0,
        description="Skip this many messages from the start. Omit to load the latest page.",
    ),
) -> JSONResponse:
    rows, total, skip, conv = await conv_svc.list_person_messages(
        session, person, settings=settings, limit=limit, offset=offset
    )
    return JSONResponse(
        content=success(
            {
                "conversationId": str(conv.id),
                "items": [_message_item(m) for m in rows],
                "total": total,
                "limit": limit,
                "offset": skip,
                "hasOlder": skip > 0,
                "hasNewer": skip + len(rows) < total,
            }
        )
    )
