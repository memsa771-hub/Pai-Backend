from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from auth_service.orchestration.state import PAIState


def _route_after_turn(state: PAIState) -> Literal["extract_facts", "run_conversation_agent"]:
    if state.get("extraction_required"):
        return "extract_facts"
    return "run_conversation_agent"


def build_pai_graph(orchestrator) -> StateGraph:
    graph = StateGraph(PAIState)

    graph.add_node("save_user_message", orchestrator.node_save_user_message)
    graph.add_node("load_student_context", orchestrator.node_load_student_context)
    graph.add_node("route_turn", orchestrator.node_route_turn)
    graph.add_node("extract_facts", orchestrator.node_extract_facts)
    graph.add_node("validate_candidates", orchestrator.node_validate_candidates)
    graph.add_node("apply_vault_changes", orchestrator.node_apply_vault_changes)
    graph.add_node("refresh_student_context", orchestrator.node_refresh_student_context)
    graph.add_node("run_conversation_agent", orchestrator.node_run_conversation_agent)
    graph.add_node("process_tasks", orchestrator.node_process_tasks)
    graph.add_node("save_assistant_message", orchestrator.node_save_assistant_message)

    graph.set_entry_point("save_user_message")
    graph.add_edge("save_user_message", "load_student_context")
    graph.add_edge("load_student_context", "route_turn")
    graph.add_conditional_edges(
        "route_turn",
        _route_after_turn,
        {
            "extract_facts": "extract_facts",
            "run_conversation_agent": "run_conversation_agent",
        },
    )
    graph.add_edge("extract_facts", "validate_candidates")
    graph.add_edge("validate_candidates", "apply_vault_changes")
    graph.add_edge("apply_vault_changes", "refresh_student_context")
    graph.add_edge("refresh_student_context", "run_conversation_agent")
    graph.add_edge("run_conversation_agent", "process_tasks")
    graph.add_edge("process_tasks", "save_assistant_message")
    graph.add_edge("save_assistant_message", END)
    return graph
