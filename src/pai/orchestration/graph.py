from __future__ import annotations

from langgraph.graph import END, StateGraph

from pai.orchestration.state import PAIState


def build_pai_graph(orchestrator) -> StateGraph:
    graph = StateGraph(PAIState)

    graph.add_node("save_user_message", orchestrator.node_save_user_message)
    graph.add_node("load_student_context", orchestrator.node_load_student_context)
    graph.add_node("route_turn", orchestrator.node_route_turn)
    graph.add_node("serve_turn", orchestrator.node_serve_turn)
    graph.add_node("process_tasks", orchestrator.node_process_tasks)
    graph.add_node("save_assistant_message", orchestrator.node_save_assistant_message)

    graph.set_entry_point("save_user_message")
    graph.add_edge("save_user_message", "load_student_context")
    graph.add_edge("load_student_context", "route_turn")
    graph.add_edge("route_turn", "serve_turn")
    graph.add_edge("serve_turn", "process_tasks")
    graph.add_edge("process_tasks", "save_assistant_message")
    graph.add_edge("save_assistant_message", END)
    return graph
