from __future__ import annotations

import uuid
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

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
chat_router = APIRouter(prefix="/api/v1", tags=["chat"])


class ConversationCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"title": "Germany MS plan"}]}
    )

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional conversation title.",
        examples=["Germany MS plan"],
    )


class MessageCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"content": "What IELTS score do I need for TU Munich?"}]
        }
    )

    content: str = Field(
        ...,
        min_length=1,
        max_length=16000,
        description="Student message.",
        examples=["What IELTS score do I need for TU Munich?"],
    )


class ChatRequest(BaseModel):
    """Unified PAI chat turn.

    PAI is one persistent counselor per Person. Conversations are topic threads only.
    Omitting conversationId continues the latest active thread (client convenience).
    Set newConversation=true to start a new topic — person Vault/memory are NOT reset.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "message": "I want MS CS in Germany under 20000 EUR",
                    "conversationId": None,
                    "newConversation": False,
                },
                {
                    "message": "What IELTS score should I target?",
                    "newConversation": True,
                    "title": "IELTS planning",
                },
                {
                    "message": "Should I learn Docker?",
                    "conversationId": "00000000-0000-0000-0000-000000000000",
                },
            ]
        },
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=16000,
        description="Student message to PAI.",
        examples=["I want MS CS in Germany under 20000 EUR"],
    )
    conversation_id: uuid.UUID | None = Field(
        default=None,
        alias="conversationId",
        description=(
            "Topic-thread UUID. Send on follow-ups within the same discussion. "
            "If omitted, continues the latest active thread unless newConversation=true."
        ),
    )
    new_conversation: bool = Field(
        default=False,
        alias="newConversation",
        description=(
            "Start a new topic thread. Does NOT clear Person Vault, goals, tasks, "
            "documents, or semantic memory — PAI still knows the student."
        ),
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Title used only when creating a new conversation thread.",
        examples=["Germany MS plan"],
    )


_AUTH_ERRORS = {
    401: {"model": ApiErrorResponse, "description": "Missing/invalid Bearer token"},
    403: {"model": ApiErrorResponse, "description": "Onboarding not completed"},
    404: {"model": ApiErrorResponse, "description": "Conversation or person not found"},
    422: {"model": ApiErrorResponse, "description": "Validation error"},
    502: {"model": ApiErrorResponse, "description": "LLM / orchestration failure"},
}


@chat_router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    summary="Send a counselor message",
    description=(
        "Primary PAI turn. Requires `Authorization: Bearer <accessToken>`.\n\n"
        "**Product model:** PAI is **one persistent counselor per Person**. "
        "A conversation is only a topic thread. New chat = new topic, not amnesia.\n\n"
        "Every turn reconstructs counselor knowledge from:\n"
        "- Person Vault + typed profile (education, goals, skills)\n"
        "- Long-term semantic memory (preferences, constraints, insights)\n"
        "- Tasks, documents, current-thread messages, and recent other-thread snippets\n\n"
        "**Thread routing:**\n"
        "- Send `conversationId` to continue the same topic.\n"
        "- Omit `conversationId` → continue latest active thread (Swagger-friendly).\n"
        "- `newConversation: true` → new topic thread; person-level memory stays intact.\n\n"
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
    conv = await conv_svc.resolve_chat_conversation(
        session,
        person,
        conversation_id=body.conversation_id,
        new_conversation=body.new_conversation,
        title=body.title,
    )
    conversation_id = conv.id

    user_msg = await conv_svc.save_user_message(session, person, conversation_id, body.message)
    gateway = getattr(request.app.state, "llm_gateway", None)
    data = await handle_user_message(
        session, settings, person, conversation_id, user_msg, gateway=gateway
    )
    return JSONResponse(content=success(data))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create conversation",
    responses={401: {"model": ApiErrorResponse}},
)
async def create_conversation(
    body: ConversationCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    conv = await conv_svc.create_conversation(session, person, title=body.title)
    return JSONResponse(
        status_code=201,
        content=success({"id": str(conv.id), "title": conv.title, "status": conv.status}),
    )


@router.get(
    "",
    summary="List conversations",
    responses={401: {"model": ApiErrorResponse}},
)
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    rows = await conv_svc.list_conversations(session, person.id, limit=limit, offset=offset)
    return JSONResponse(
        content=success(
            {
                "items": [
                    {
                        "id": str(c.id),
                        "title": c.title,
                        "status": c.status,
                        "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
                    }
                    for c in rows
                ]
            }
        )
    )


@router.get(
    "/threads",
    summary="All conversations with Q&A flow",
    description=(
        "Lists every conversation with a readable dialogue flow: "
        "what the student asked and what PAI replied (turn by turn)."
    ),
    responses={401: {"model": ApiErrorResponse}},
)
async def list_conversation_threads(
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    items = await conv_svc.list_conversation_threads(
        session, person.id, limit=limit, offset=offset
    )
    return JSONResponse(content=success({"items": items}))


@router.get(
    "/{conversation_id}",
    summary="Get conversation",
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    conv = await conv_svc.get_conversation_owned(session, person.id, conversation_id)
    return JSONResponse(
        content=success(
            {
                "id": str(conv.id),
                "title": conv.title,
                "status": conv.status,
                "topic": conv.topic,
            }
        )
    )


@router.get(
    "/{conversation_id}/flow",
    summary="One conversation Q&A flow",
    description="User ask → PAI reply turns for a single conversation.",
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def get_conversation_flow(
    conversation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    data = await conv_svc.get_conversation_flow(session, person.id, conversation_id)
    return JSONResponse(content=success(data))


@router.delete(
    "/{conversation_id}",
    summary="Soft-delete conversation",
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    await conv_svc.delete_conversation(session, person.id, conversation_id)
    return JSONResponse(content=success({"message": "Conversation deleted."}))


@router.get(
    "/{conversation_id}/messages",
    summary="List messages",
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def get_messages(
    conversation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    rows = await conv_svc.list_messages(session, person.id, conversation_id)
    return JSONResponse(
        content=success(
            {
                "items": [
                    {
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "createdAt": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in rows
                ]
            }
        )
    )


@router.post(
    "/{conversation_id}/messages",
    summary="Send message (compat)",
    description=(
        "Same orchestration as `POST /api/v1/chat` for an existing conversation. "
        "Prefer `/api/v1/chat` for new clients."
    ),
    responses=_AUTH_ERRORS,
)
async def post_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(require_onboarding_complete),
) -> JSONResponse:
    user_msg = await conv_svc.save_user_message(session, person, conversation_id, body.content)
    gateway = getattr(request.app.state, "llm_gateway", None)
    data = await handle_user_message(
        session, settings, person, conversation_id, user_msg, gateway=gateway
    )
    return JSONResponse(content=success(data))
