from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ResearchHit:
    title: str
    url: str
    snippet: str


@dataclass
class ResearchResult:
    ok: bool
    query: str
    summary: str = ""
    hits: list[ResearchHit] = field(default_factory=list)
    error: str = ""
    configured: bool = True

    def as_counselor_text(self) -> str:
        if not self.ok:
            return self.error or "Web search failed."
        lines: list[str] = []
        if self.summary:
            lines.append(f"Summary: {self.summary}")
        for i, hit in enumerate(self.hits, 1):
            lines.append(f"{i}. {hit.title}\n   {hit.url}\n   {hit.snippet}")
        return "\n".join(lines) if lines else "No results found."


