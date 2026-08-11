from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth_service.conversations.models import Conversation, Message, OrchestrationRun
from auth_service.core.errors import AuthError, PersonNotFoundError
from auth_service.person.models import Person


class ConversationNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__(code="CONVERSATION_NOT_FOUND", message="Conversation not found.", status_code=404)


async def create_conversation(
    session: AsyncSession, person: Person, *, title: str | None = None
) -> Conversation:
    row = Conversation(person_id=person.id, title=title or "New conversation")
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_conversations(
    session: AsyncSession, person_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.person_id == person_id, Conversation.status != "deleted")
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_conversation_owned(
    session: AsyncSession, person_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.person_id == person_id,
            Conversation.status != "deleted",
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ConversationNotFoundError()
    return row


async def delete_conversation(
    session: AsyncSession, person_id: uuid.UUID, conversation_id: uuid.UUID
) -> None:
    conv = await get_conversation_owned(session, person_id, conversation_id)
    conv.status = "deleted"
    await session.commit()


async def list_messages(
    session: AsyncSession, person_id: uuid.UUID, conversation_id: uuid.UUID
) -> list[Message]:
    await get_conversation_owned(session, person_id, conversation_id)
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.person_id == person_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def save_user_message(
    session: AsyncSession,
    person: Person,
    conversation_id: uuid.UUID,
    content: str,
) -> Message:
    await get_conversation_owned(session, person.id, conversation_id)
    msg = Message(
        conversation_id=conversation_id,
        person_id=person.id,
        role="user",
        content=content,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def save_assistant_message(
    session: AsyncSession,
    person: Person,
    conversation_id: uuid.UUID,
    content: str,
    *,
    provider: str | None,
    model: str | None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        person_id=person.id,
        role="assistant",
        content=content,
        model_provider=provider,
        model_name=model,
    )
    session.add(msg)
    conv = await session.get(Conversation, conversation_id)
    if conv and conv.title in (None, "New conversation"):
        conv.title = content[:80]
    await session.commit()
    await session.refresh(msg)
    return msg


async def start_orchestration_run(
    session: AsyncSession,
    person: Person,
    *,
    conversation_id: uuid.UUID | None,
    run_type: str,
) -> OrchestrationRun:
    run = OrchestrationRun(
        person_id=person.id,
        conversation_id=conversation_id,
        run_type=run_type,
        status="running",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run
