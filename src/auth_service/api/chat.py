from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.config import Settings, get_settings
from auth_service.conversations import service as conv_svc
from auth_service.dependencies import get_db, resolve_person_from_token
from auth_service.ingestion.chat import handle_user_message
from auth_service.schemas import ApiErrorResponse, success

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
    """Unified PAI chat turn — creates a conversation when conversationId is omitted."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "message": "I want MS CS in Germany under 20000 EUR",
                    "conversationId": None,
                    "title": "Germany MS plan",
                },
                {
                    "message": "What IELTS score should I target?",
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
        description="Existing conversation UUID. Omit or null to start a new thread.",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Title used only when creating a new conversation.",
        examples=["Germany MS plan"],
    )


_AUTH_ERRORS = {
    401: {"model": ApiErrorResponse, "description": "Missing/invalid Bearer token"},
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
        "**Swagger:** Authorize with `data.accessToken` from login (token only, no `Bearer` word).\n\n"
        "**Critical:** Omit `conversationId` only to start a **new** thread. For every "
        "follow-up, send the same `conversationId` from the previous response "
        "(`data.conversationId`). Creating a new id each message wipes dialogue history "
        "for that thread (profile Vault still persists)."
    ),
    responses=_AUTH_ERRORS,
)
async def chat(
    body: ChatRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    if body.conversation_id is None:
        conv = await conv_svc.create_conversation(session, person, title=body.title)
        conversation_id = conv.id
    else:
        await conv_svc.get_conversation_owned(session, person.id, body.conversation_id)
        conversation_id = body.conversation_id

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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
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
    person=Depends(resolve_person_from_token),
) -> JSONResponse:
    user_msg = await conv_svc.save_user_message(session, person, conversation_id, body.content)
    gateway = getattr(request.app.state, "llm_gateway", None)
    data = await handle_user_message(
        session, settings, person, conversation_id, user_msg, gateway=gateway
    )
    return JSONResponse(content=success(data))
