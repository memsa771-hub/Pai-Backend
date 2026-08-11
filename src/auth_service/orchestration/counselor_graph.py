from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from auth_service.config import Settings
from auth_service.llm.gateway import LLMGateway
from auth_service.llm.schemas import LLMMessage, LLMResponse, LLMToolCall, LLMToolCallFunction
from auth_service.memory.service import PersonMemoryService
from auth_service.orchestration.prompts import render_template
from auth_service.orchestration.schemas import ConversationResult
from auth_service.tools.base import ToolContext
from auth_service.tools.registry import ToolRegistry, build_default_registry

logger = logging.getLogger(__name__)


class CounselorToolState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    round: int
    max_rounds: int
    final: ConversationResult | None
    tool_trace: list[dict[str, Any]]
    pending_tool_calls: list[dict[str, Any]]


def build_counselor_tool_graph(
    *,
    gateway: LLMGateway,
    settings: Settings,
    registry: ToolRegistry,
    tool_ctx: ToolContext,
) -> Any:
    """LangGraph ReAct loop: reason → tools → reason → structured reply."""

    async def agent_node(state: CounselorToolState) -> dict[str, Any]:
        round_n = int(state.get("round") or 0)
        max_rounds = int(state.get("max_rounds") or settings.counselor_max_tool_rounds)
        raw_messages = list(state.get("messages") or [])
        messages = [_dict_to_llm_message(m) for m in raw_messages]

        if round_n >= max_rounds:
            result = await _finalize_structured(gateway, messages)
            return {"final": result, "round": round_n + 1, "pending_tool_calls": []}

        response = await gateway.run(
            task="student_conversation",
            messages=messages,
            temperature=0.3,
            tools=registry.openai_tools(),
            tool_choice="auto",
        )
        assert isinstance(response, LLMResponse)

        if response.has_tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
            return {
                "messages": raw_messages + [assistant_msg],
                "round": round_n + 1,
                "pending_tool_calls": assistant_msg["tool_calls"],
                "final": None,
            }

        result = await _coerce_or_finalize(gateway, messages, response.content)
        return {
            "messages": raw_messages + [{"role": "assistant", "content": response.content or ""}],
            "final": result,
            "round": round_n + 1,
            "pending_tool_calls": [],
        }

    async def tools_node(state: CounselorToolState) -> dict[str, Any]:
        pending = list(state.get("pending_tool_calls") or [])
        raw_messages = list(state.get("messages") or [])
        tool_messages: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = list(state.get("tool_trace") or [])

        for raw_tc in pending:
            tc = _normalize_tool_call(raw_tc)
            result = await registry.execute(tc.function.name, tc.function.arguments, tool_ctx)
            trace.append(
                {"tool": tc.function.name, "ok": result.ok, "preview": result.content[:240]}
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result.content,
                }
            )
        return {
            "messages": raw_messages + tool_messages,
            "tool_trace": trace,
            "pending_tool_calls": [],
        }

    def route_after_agent(state: CounselorToolState) -> Literal["tools", "end"]:
        if state.get("final") is not None:
            return "end"
        if state.get("pending_tool_calls"):
            return "tools"
        return "end"

    graph = StateGraph(CounselorToolState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


async def run_counselor_with_tools(
    *,
    gateway: LLMGateway,
    settings: Settings,
    memory: PersonMemoryService,
    prompt_vars: dict[str, Any],
    person_id: str,
    conversation_id: str,
    registry: ToolRegistry | None = None,
) -> tuple[ConversationResult, list[dict[str, Any]]]:
    registry = registry or build_default_registry()
    tool_ctx = ToolContext(
        settings=settings,
        memory=memory,
        person_id=person_id,
        conversation_id=conversation_id,
    )
    system = render_template("system.v1.jinja2")
    user_prompt = render_template("student_conversation.v1.jinja2", **prompt_vars)
    seed_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    if not settings.enable_counselor_tools:
        result = await _finalize_structured(
            gateway, [_dict_to_llm_message(m) for m in seed_messages]
        )
        return result, []

    graph = build_counselor_tool_graph(
        gateway=gateway,
        settings=settings,
        registry=registry,
        tool_ctx=tool_ctx,
    )
    final_state = await graph.ainvoke(
        {
            "messages": seed_messages,
            "round": 0,
            "max_rounds": settings.counselor_max_tool_rounds,
            "final": None,
            "tool_trace": [],
            "pending_tool_calls": [],
        }
    )
    result = final_state.get("final")
    if result is None:
        result = await _finalize_structured(
            gateway,
            [_dict_to_llm_message(m) for m in (final_state.get("messages") or seed_messages)],
        )
    return result, list(final_state.get("tool_trace") or [])


def _normalize_tool_call(raw: dict[str, Any] | LLMToolCall) -> LLMToolCall:
    if isinstance(raw, LLMToolCall):
        return raw
    fn = raw.get("function") or {}
    args = fn.get("arguments", "{}")
    if not isinstance(args, str):
        args = json.dumps(args)
    return LLMToolCall(
        id=str(raw.get("id") or "tool_call"),
        function=LLMToolCallFunction(name=str(fn.get("name") or ""), arguments=args),
    )


def _dict_to_llm_message(raw: dict[str, Any]) -> LLMMessage:
    tool_calls = None
    if raw.get("tool_calls"):
        tool_calls = [_normalize_tool_call(tc) for tc in raw["tool_calls"]]
    return LLMMessage(
        role=raw["role"],
        content=raw.get("content"),
        name=raw.get("name"),
        tool_call_id=raw.get("tool_call_id"),
        tool_calls=tool_calls,
    )


async def _finalize_structured(
    gateway: LLMGateway, messages: list[LLMMessage]
) -> ConversationResult:
    out = await gateway.run(
        task="student_conversation",
        messages=messages,
        output_schema=ConversationResult,
        temperature=0.4,
    )
    assert isinstance(out, ConversationResult)
    return out


async def _coerce_or_finalize(
    gateway: LLMGateway, messages: list[LLMMessage], content: str
) -> ConversationResult:
    text = (content or "").strip()
    if text.startswith("{"):
        try:
            return ConversationResult.model_validate(json.loads(text))
        except Exception:
            pass
    if text.startswith("```"):
        body = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return ConversationResult.model_validate(json.loads(body))
        except Exception:
            pass
    return await _finalize_structured(
        gateway,
        messages
        + [
            LLMMessage(role="assistant", content=content or ""),
            LLMMessage(
                role="user",
                content=(
                    "Convert your last answer into ConversationResult JSON only "
                    "(reply, known_facts_used, observations, suggested_next_step, "
                    "next_question, task_proposals)."
                ),
            ),
        ],
    )
