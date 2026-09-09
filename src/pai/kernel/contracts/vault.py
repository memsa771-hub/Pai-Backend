"""ORM-free, owner-scoped contracts consumed by other departments."""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field
from pai.kernel.contracts.schemas import VaultCandidate


class StudentIdentity(BaseModel):
    id: UUID
    full_name: str | None = None
    preferred_name: str | None = None


class DocumentEvidence(BaseModel):
    person_id: UUID
    document_id: UUID
    observations: list[VaultCandidate]


class VaultSnapshot(BaseModel):
    person_id: UUID
    revision: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    completion: dict[str, Any] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)


class VaultReader(Protocol):
    async def get_snapshot(self, person_id: UUID) -> VaultSnapshot | None: ...

    async def get_identity(self, person_id: UUID) -> StudentIdentity | None: ...

    async def get_known_facts(self, person_id: UUID) -> list[str]: ...

    async def get_existing_belief(self, person_id: UUID, field_key: str, *, spec=None): ...

    async def lock_revision(self, person_id: UUID) -> int | None:
        """Hold the owner's write fence until transaction completion; reject deletion."""
        ...


class VaultWriter(Protocol):
    async def evaluate_observations(self, person_id: UUID, observations: list[VaultCandidate]): ...

    async def submit_observations(self, person_id: UUID, observations: list[VaultCandidate], **policy): ...

    async def submit_document_evidence(self, evidence: DocumentEvidence, **policy): ...
