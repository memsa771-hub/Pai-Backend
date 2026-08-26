"""Accept a living goal only when extraction classified a grounded life aim.

Meaning (life aim vs this-turn action) is the model's job — any language,
including Roman Urdu. Code does not keep verb lists. It only refuses writes
that are not classified as life_aim or whose evidence is not in the message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_GOAL_NOW = "goal:now"
_LIFE_AIM = "life_aim"


@dataclass(frozen=True)
class GoalHit:
    object_key: str
    object_label: str
    stance: str
    reason: str | None
    evidence: str


def resolve_goal_hit(text: str, llm_goal: Any | None = None) -> GoalHit | None:
    """LLM current_goal is a classification. Missing kind fails closed."""
    if llm_goal is None:
        return None
    if (getattr(llm_goal, "kind", None) or "none") != _LIFE_AIM:
        return None
    evidence = (getattr(llm_goal, "evidence_text", None) or "").strip()
    intent = (getattr(llm_goal, "intent", None) or "").strip() or evidence
    if len(intent) < 4:
        return None
    span = evidence or intent
    if not _grounded(span, text):
        return None
    mode = getattr(llm_goal, "mode", None)
    if mode not in ("pursuing", "exploring"):
        mode = "pursuing"
    return GoalHit(
        object_key=_GOAL_NOW,
        object_label=intent[:240],
        stance=mode,
        reason="pivot" if getattr(llm_goal, "supersedes_previous", False) else None,
        evidence=span[:240],
    )


def normalize_intent(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip(" .").casefold()


def _grounded(span: str, source: str) -> bool:
    """Evidence must be a span of the student message, not a model rewrite."""
    ev = _fold(span)
    src = _fold(source)
    if len(ev) < 4 or not src:
        return False
    if ev in src:
        return True
    tokens = [tok for tok in re.findall(r"\w+", ev, flags=re.UNICODE) if len(tok) >= 2]
    if len(tokens) < 2:
        return False
    pos = 0
    for tok in tokens:
        found = src.find(tok, pos)
        if found < 0:
            return False
        pos = found + len(tok)
    return True


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().casefold()
