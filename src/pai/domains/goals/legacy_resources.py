"""Goal-owned persistence for legacy /person/goals endpoints."""
from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pai.domains.goals.models import Goal
from pai.domains.student.public import lock_owner, refresh_profile_projection
from pai.kernel.contracts.vault import StudentIdentity as Person
from pai.kernel.errors import PersonNotFoundError

MODELS = {"goals": Goal}

async def list_resources(
    session: AsyncSession,
    model: type,
    person_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Any]:
    if model not in MODELS.values():
        raise ValueError("Resource model belongs to another department")
    result = await session.execute(
        select(model).where(model.person_id == person_id).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def create_resource(
    session: AsyncSession,
    model: type,
    person: Person,
    data: dict[str, Any],
) -> Any:
    if model not in MODELS.values():
        raise ValueError("Resource model belongs to another department")
    await lock_owner(session, person.id)
    row = model(person_id=person.id, **data)
    session.add(row)
    await session.flush()
    scopes = ["application"]
    if data.get("goal_type", "").lower() in ("relocation", "mobility", "relocate"):
        scopes.append("mobility")
    await refresh_profile_projection(session, person.id, scopes=scopes)
    from pai.domains.goals.service import mark_intelligence_stale_for_vault_update
    await mark_intelligence_stale_for_vault_update(session, person.id, model.__tablename__)
    await session.commit()
    await session.refresh(row)
    return row


async def update_resource(
    session: AsyncSession,
    model: type,
    person: Person,
    resource_id: uuid.UUID,
    data: dict[str, Any],
) -> Any:
    if model not in MODELS.values():
        raise ValueError("Resource model belongs to another department")
    await lock_owner(session, person.id)
    result = await session.execute(
        select(model).where(model.id == resource_id, model.person_id == person.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise PersonNotFoundError("Resource not found.")
    for key, val in data.items():
        if hasattr(row, key) and val is not None:
            setattr(row, key, val)
    await session.flush()
    await refresh_profile_projection(session, person.id)
    from pai.domains.goals.service import mark_intelligence_stale_for_vault_update
    await mark_intelligence_stale_for_vault_update(session, person.id, model.__tablename__)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_resource(
    session: AsyncSession,
    model: type,
    person: Person,
    resource_id: uuid.UUID,
) -> None:
    if model not in MODELS.values():
        raise ValueError("Resource model belongs to another department")
    await lock_owner(session, person.id)
    result = await session.execute(
        select(model).where(model.id == resource_id, model.person_id == person.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise PersonNotFoundError("Resource not found.")
    await session.delete(row)
    await session.flush()
    await refresh_profile_projection(session, person.id)
    from pai.domains.goals.service import mark_intelligence_stale_for_vault_update
    await mark_intelligence_stale_for_vault_update(session, person.id, model.__tablename__)
    await session.commit()
