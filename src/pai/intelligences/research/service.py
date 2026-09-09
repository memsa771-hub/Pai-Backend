"""Research intelligence — verify current external facts. Does not write domains."""

from __future__ import annotations

from typing import Any

from pai.capabilities.search import search
from pai.platform.latency import timed


from pai.kernel.contracts.research import ResearchHit, ResearchResult


@timed("web_search")
async def research_query(
    *,
    query: str,
    api_key: str,
    search_depth: str,
    max_results: int,
    topic: str = "general",
) -> ResearchResult:
    raw: dict[str, Any] = await search(
        query=query,
        api_key=api_key,
        search_depth=search_depth,
        max_results=max_results,
        topic=topic,
    )
    if not raw.get("ok"):
        return ResearchResult(
            ok=False,
            query=query,
            error=str(raw.get("error") or "Web search failed."),
        )
    hits = [
        ResearchHit(
            title=str(item.get("title") or "Untitled"),
            url=str(item.get("url") or ""),
            snippet=(str(item.get("content") or ""))[:400],
        )
        for item in (raw.get("results") or [])[:max_results]
    ]
    return ResearchResult(
        ok=True,
        query=query,
        summary=str(raw.get("answer") or ""),
        hits=hits,
    )
