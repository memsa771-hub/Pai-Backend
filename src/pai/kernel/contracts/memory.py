"""Independent input to Memory; no Vault catalog or ORM dependency."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MemoryObservation:
    memory_key: str
    content: str
    kind: str
    status: str
    confidence: float
    importance: float
    assertion_status: str
    source_references: list[str] = field(default_factory=list)
    evidence: str = ""
    belongs_to: str = "profile"
    related: list[str] = field(default_factory=list)
    field_key: str | None = None
    value: Any = None


