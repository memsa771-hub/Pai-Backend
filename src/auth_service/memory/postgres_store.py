from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

from agentspan.agents.semantic_memory import MemoryEntry, MemoryStore
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.memory.models import SemanticMemoryRow


class AsyncPostgresMemoryStore:
    """Async Postgres store used by PersonMemoryService (AgentSpan-compatible entries)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        person_id: uuid.UUID,
    ) -> None:
        self._session_factory = session_factory
        self._person_id = person_id

    async def add(self, entry: MemoryEntry) -> str:
        entry_id = entry.id or hashlib.sha256(
            f"{entry.content}{time.time()}".encode()
        ).hexdigest()[:16]
        created_at = entry.created_at or time.time()
        async with self._session_factory() as session:
            row = SemanticMemoryRow(
                id=uuid.uuid4(),
                person_id=self._person_id,
                content=entry.content,
                entry_metadata=dict(entry.metadata or {}),
                external_id=entry_id,
            )
            session.add(row)
            await session.commit()
        entry.id = entry_id
        entry.created_at = created_at
        return entry_id

    async def search(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        # Cap rows before Python ranking — full-table load does not scale.
        from auth_service.config import get_settings

        scan_limit = max(top_k, get_settings().semantic_memory_scan_limit)
        async with self._session_factory() as session:
            result = await session.execute(
                select(SemanticMemoryRow)
                .where(SemanticMemoryRow.person_id == self._person_id)
                .order_by(SemanticMemoryRow.created_at.desc())
                .limit(scan_limit)
            )
            rows = list(result.scalars().all())
        return _rank_entries(query, rows, top_k)

    async def delete(self, memory_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(SemanticMemoryRow).where(
                    SemanticMemoryRow.person_id == self._person_id,
                    SemanticMemoryRow.external_id == memory_id,
                )
            )
            await session.commit()
            return (result.rowcount or 0) > 0

    async def clear(self) -> None:
        async with self._session_factory() as session:
            await session.execute(
                delete(SemanticMemoryRow).where(
                    SemanticMemoryRow.person_id == self._person_id
                )
            )
            await session.commit()

    async def list_all(self) -> list[MemoryEntry]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SemanticMemoryRow).where(
                    SemanticMemoryRow.person_id == self._person_id
                )
            )
            rows = list(result.scalars().all())
        return [_row_to_entry(r) for r in rows]


class InProcessMemoryStore(MemoryStore):
    """AgentSpan MemoryStore for tests / ephemeral sessions."""

    def __init__(self) -> None:
        self._memories: dict[str, MemoryEntry] = {}

    def add(self, entry: MemoryEntry) -> str:
        if not entry.id:
            entry.id = hashlib.sha256(f"{entry.content}{time.time()}".encode()).hexdigest()[:16]
        if not entry.created_at:
            entry.created_at = time.time()
        self._memories[entry.id] = entry
        return entry.id

    def search(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        query_words = set(query.lower().split())
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._memories.values():
            entry_words = set(entry.content.lower().split())
            if not query_words or not entry_words:
                score = 0.0
            else:
                intersection = query_words & entry_words
                union = query_words | entry_words
                score = len(intersection) / len(union) if union else 0.0
            scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for score, entry in scored[:top_k] if score > 0]

    def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    def clear(self) -> None:
        self._memories.clear()

    def list_all(self) -> list[MemoryEntry]:
        return list(self._memories.values())


def _row_to_entry(row: SemanticMemoryRow) -> MemoryEntry:
    meta: dict[str, Any] = dict(row.entry_metadata or {})
    return MemoryEntry(
        id=row.external_id,
        content=row.content,
        metadata=meta,
        created_at=row.created_at.timestamp() if row.created_at else 0.0,
    )


def _rank_entries(
    query: str, rows: list[SemanticMemoryRow], top_k: int
) -> list[MemoryEntry]:
    """Jaccard overlap ranking (same heuristic as AgentSpan InMemoryStore)."""
    query_words = set(query.lower().split())
    scored: list[tuple[float, MemoryEntry]] = []
    for row in rows:
        entry = _row_to_entry(row)
        entry_words = set(entry.content.lower().split())
        if not query_words or not entry_words:
            score = 0.0
        else:
            intersection = query_words & entry_words
            union = query_words | entry_words
            score = len(intersection) / len(union) if union else 0.0
        scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for score, entry in scored[:top_k] if score > 0]
