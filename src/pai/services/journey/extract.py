"""Capture the student's current goal in their own words. No country/uni taxonomy."""

from __future__ import annotations

import re
from dataclasses import dataclass

_GOAL_NOW = "goal:now"

# Last matching clause is the live brief (pivots overwrite earlier wants).
_CLAUSE = re.compile(
    r"(?P<lead>"
    r"i\s+(?:want(?:\s+to)?|wanna|decided\s+to|need\s+to|would\s+like\s+to)|"
    r"my\s+goal\s+is|"
    r"i(?:'m| am)\s+(?:planning\s+to|looking\s+to|aiming\s+to|going\s+to|"
    r"considering|thinking\s+about)"
    r")\s+(?P<body>[^?!.]{3,220})",
    re.I,
)
_PIVOT = re.compile(
    r"\b(changed my mind|not local(?:ly)?|no longer|instead(?: of)?|"
    r"rather than|switch(?:ing)? to|forget that|not anymore)\b",
    re.I,
)
_META = re.compile(
    r"^(help|you to|you|advice|a question|to ask|your help|know|understand)\b",
    re.I,
)
_EXPLORING = re.compile(r"\b(considering|thinking about|maybe|might)\b", re.I)
_FILLER = re.compile(
    r"^(?:i\s+(?:want(?:\s+to)?|wanna|decided\s+to|need\s+to|would\s+like\s+to)|"
    r"my\s+goal\s+is|"
    r"i(?:'m| am)\s+(?:planning\s+to|looking\s+to|aiming\s+to|going\s+to|"
    r"considering|thinking\s+about))\s+",
    re.I,
)
_COST = re.compile(r"too\s+expensive|can'?t\s+afford|cannot\s+afford|\btuition\b", re.I)


@dataclass(frozen=True)
class GoalHit:
    object_key: str
    object_label: str
    stance: str
    reason: str | None
    evidence: str


def extract_goal(text: str) -> GoalHit | None:
    raw = re.sub(r"\s+", " ", (text or "")).strip()
    if len(raw) < 10:
        return None
    clause = _last_clause(raw)
    if clause is None and _PIVOT.search(raw):
        clause = raw
    if clause is None:
        return None
    intent = _clean_intent(clause)
    if len(intent) < 4 or _META.match(intent):
        return None
    return GoalHit(
        object_key=_GOAL_NOW,
        object_label=intent[:240],
        stance="exploring" if _EXPLORING.search(clause) else "pursuing",
        reason=_reason(raw),
        evidence=raw[:240],
    )


def normalize_intent(text: str) -> str:
    return _FILLER.sub("", re.sub(r"\s+", " ", text or "").strip(" .")).casefold()


def _last_clause(text: str) -> str | None:
    matches = list(_CLAUSE.finditer(text))
    if not matches:
        return None
    match = matches[-1]
    return f"{match.group('lead')} {match.group('body')}".strip()


def _clean_intent(clause: str) -> str:
    body = _FILLER.sub("", clause).strip(" .,")
    return re.sub(r"\s+", " ", body)


def _reason(text: str) -> str | None:
    if _PIVOT.search(text):
        return "pivot"
    if _COST.search(text):
        return "cost"
    return None
