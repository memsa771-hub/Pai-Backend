from __future__ import annotations

import logging
from typing import Any

from pai.tools.base import ToolContext, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Online search via Tavily — used for deadlines, programs, scholarships, etc."""

    name = "web_search"
    description = (
        "Search the live web for current, factual information relevant to the student "
        "(university requirements, deadlines, scholarships, visa rules, rankings, news). "
        "Do not use for personal profile facts already in the vault."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Focused search query. Include the student's current country "
                    "and study destination; do not assume Pakistan."
                ),
            },
            "topic": {
                "type": "string",
                "enum": ["general", "news"],
                "description": "Search topic bias.",
                "default": "general",
            },
        },
        "required": ["query"],
    }

    def openai_tool_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    async def ainvoke(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = str(args.get("query") or "").strip()
        if not query:
            return ToolResult(name=self.name, ok=False, content="Missing query.")
        api_key = (ctx.settings.tavily_api_key or "").strip()
        if not api_key:
            return ToolResult(
                name=self.name,
                ok=False,
                content=(
                    "Web search is unavailable: TAVILY_API_KEY is not configured. "
                    "Answer from known student context only and say current web facts "
                    "could not be verified."
                ),
                data={"configured": False},
            )
        try:
            from tavily import AsyncTavilyClient
        except ImportError:
            return ToolResult(
                name=self.name,
                ok=False,
                content="tavily-python is not installed.",
            )
        topic = str(args.get("topic") or "general")
        client = AsyncTavilyClient(api_key=api_key)
        try:
            response = await client.search(
                query=query,
                search_depth=ctx.settings.tavily_search_depth,
                max_results=ctx.settings.tavily_max_results,
                include_answer=True,
                topic=topic,
            )
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return ToolResult(
                name=self.name,
                ok=False,
                content=f"Web search failed: {exc}",
            )
        results = response.get("results") or []
        answer = response.get("answer") or ""
        lines: list[str] = []
        if answer:
            lines.append(f"Summary: {answer}")
        for i, item in enumerate(results[: ctx.settings.tavily_max_results], 1):
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = (item.get("content") or "")[:400]
            lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
        content = "\n".join(lines) if lines else "No results found."
        return ToolResult(
            name=self.name,
            ok=True,
            content=content,
            data={"result_count": len(results), "query": query},
        )
