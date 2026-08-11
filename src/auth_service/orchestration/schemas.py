from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


Explicitness = Literal["explicit", "strongly_implied", "uncertain"]
CandidateOutcome = Literal[
    "accept", "reinforce", "pending_confirmation", "conflict", "reject"
]


class VaultCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field_key: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    explicitness: Explicitness = "explicit"
    source_type: Literal[
        "chat", "document", "manual", "auth", "system", "linkedin", "social"
    ] = "chat"
    source_reference: str
    evidence_text: str
    is_correction: bool = False
    requires_confirmation: bool = False
    rationale_summary: str = ""


class CandidateResult(BaseModel):
    candidate: VaultCandidate
    outcome: CandidateOutcome
    rationale_summary: str = ""


class VaultChange(BaseModel):
    field_key: str
    status: str
    confidence: float


class PendingConfirmation(BaseModel):
    field_key: str
    value: Any
    evidence_text: str
    source_reference: str


class TaskProposal(BaseModel):
    title: str
    detail: str | None = None
    requires_confirmation: bool = False


class TaskResult(BaseModel):
    title: str
    status: str
    task_id: str | None = None
    detail: str | None = None


class ConversationResult(BaseModel):
    reply: str
    known_facts_used: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None
    next_question: str | None = None
    task_proposals: list[TaskProposal] = Field(default_factory=list)


class FactExtractionResult(BaseModel):
    fact_candidates: list[VaultCandidate] = Field(default_factory=list)


class RunError(BaseModel):
    code: str
    message: str
    step: str | None = None
