from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.student.person.models import Person, VaultHistory
from pai.kernel.contracts.schemas import VaultCandidate


class TypedApplyResult:
    __slots__ = ("field_key", "status", "confidence")

    def __init__(self, field_key: str, status: str, confidence: float) -> None:
        self.field_key = field_key
        self.status = status
        self.confidence = confidence


async def _log_typed_history(
    session: AsyncSession,
    person: Person,
    field_key: str,
    *,
    old_value: Any,
    new_value: Any,
    candidate: VaultCandidate,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> None:
    if person.vault is None:
        return
    session.add(
        VaultHistory(
            vault_id=person.vault.id,
            field_key=field_key,
            action="updated" if old_value is not None else "created",
            old_value=old_value,
            new_value=new_value,
            actor_type="system",
            actor_id=str(person.id),
            entity_type=entity_type,
            entity_id=entity_id,
            reason=(
                f"{candidate.source_type}:{candidate.source_reference}:"
                f"{(candidate.rationale_summary or '')[:180]}"
            ),
        )
    )


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    return [value]


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


