from __future__ import annotations

from pai.conversations.service import messages_to_flow
from pai.conversations.models import Message


def _msg(role: str, content: str) -> Message:
    m = Message(role=role, content=content)
    return m


def test_messages_to_flow_pairs_user_assistant():
    flow = messages_to_flow(
        [
            _msg("user", "I want Germany"),
            _msg("assistant", "Budget?"),
            _msg("user", "20k EUR"),
            _msg("assistant", "Got it."),
        ]
    )
    assert len(flow) == 2
    assert flow[0]["user"] == "I want Germany"
    assert flow[0]["assistant"] == "Budget?"
    assert flow[1]["user"] == "20k EUR"
    assert flow[1]["assistant"] == "Got it."


def test_messages_to_flow_handles_orphan_user():
    flow = messages_to_flow([_msg("user", "Hello")])
    assert len(flow) == 1
    assert flow[0]["user"] == "Hello"
    assert flow[0]["assistant"] is None


def test_messages_to_flow_handles_opening_first():
    flow = messages_to_flow(
        [
            _msg("assistant", "Hi — I'm PAI."),
            _msg("user", "What IELTS should I target?"),
            _msg("assistant", "6.5 overall is a common bar."),
        ]
    )
    assert flow[0]["user"] is None
    assert flow[0]["assistant"] == "Hi — I'm PAI."
    assert flow[1]["user"] == "What IELTS should I target?"
    assert flow[1]["assistant"] == "6.5 overall is a common bar."
