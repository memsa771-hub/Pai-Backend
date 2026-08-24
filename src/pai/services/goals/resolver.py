"""Goal resolver — cheap, synchronous, no extra LLM call on the chat path.

Decision logic:
  1. GoalExtract from fact extraction (already computed) tells us kind/intent/mode.
  2. Only life_aim with confidence signals trigger goal writes.
  3. Return action: create | create_secondary | switch | reinforce | none
  4. create_secondary = second goal without changing active_goal_id.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pai.services.goals.service import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DRAFT,
    activate_goal,
    enqueue_goal_intelligence_job,
    find_matching_goal,
    get_conversation_active_goal,
    switch_conversation_active_goal,
    upsert_goal_from_anchors,
)
from pai.services.person.models import Goal

logger = logging.getLogger(__name__)

_LIFE_AIM = "life_aim"


@dataclass
class ResolverResult:
    action: str  # "create" | "create_secondary" | "switch" | "reinforce" | "none"
    goal: Goal | None
    intelligence_enqueued: bool


def _classify_goal_type(intent: str, anchors: dict[str, Any]) -> str:
    """Derive goal_type from intent text and anchor hints."""
    lower = intent.casefold()
    if anchors.get("goal_type"):
        return anchors["goal_type"]
    if any(kw in lower for kw in ("ms ", "msc", "bachelor", "phd", "mba", "masters", "degree", "university", "admission")):
        return "admission"
    if any(kw in lower for kw in ("internship", "intern")):
        return "internship"
    if any(kw in lower for kw in ("job", "swe", "engineer", "developer", "analyst", "role", "position", "full-time")):
        return "job"
    return "general"


def _extract_anchors_from_intent(intent: str, goal_type: str) -> dict[str, Any]:
    """Best-effort anchor extraction from intent string (no LLM)."""
    anchors: dict[str, Any] = {"goal_type": goal_type}
    lower = intent.casefold()

    # Country hints
    country_map = {
        "germany": "DE", "china": "CN", "canada": "CA", "uk": "GB",
        "usa": "US", "australia": "AU", "dubai": "AE", "uae": "AE",
        "sweden": "SE", "netherlands": "NL", "france": "FR", "turkey": "TR",
        "singapore": "SG", "malaysia": "MY", "new zealand": "NZ",
    }
    for name, code in country_map.items():
        if name in lower:
            anchors["target_country"] = code
            break

    # Degree level
    if goal_type == "admission":
        if re.search(r"\bphd\b|\bdoctor", lower):
            anchors["degree_level"] = "phd"
        elif re.search(r"\bms\b|m\.s|msc|masters?\b", lower):
            anchors["degree_level"] = "ms"
        elif re.search(r"\bbs\b|b\.s|bachelor", lower):
            anchors["degree_level"] = "bs"
        elif re.search(r"\bmba\b", lower):
            anchors["degree_level"] = "mba"

    # Program (very light)
    prog_map = {
        "cs": "computer science", "computer science": "computer science",
        "ai": "artificial intelligence", "ml": "machine learning",
        "data science": "data science", "electrical engineering": "electrical engineering",
        "mechanical engineering": "mechanical engineering",
    }
    for kw, prog in prog_map.items():
        if kw in lower:
            anchors["program"] = prog
            break

    return anchors


def _is_clear_switch(
    new_intent: str,
    active_goal: Goal | None,
) -> bool:
    """Return True when the message clearly references a *different* pursuit."""
    if active_goal is None:
        return False
    from pai.services.goals.service import _norm, _anchor_match_score

    new_anchors = _extract_anchors_from_intent(new_intent, active_goal.goal_type)
    score = _anchor_match_score(active_goal, new_anchors)
    return score < 0.4  # low overlap = different pursuit


async def resolve(
    session: AsyncSession,
    person_id: uuid.UUID,
    conversation_id: uuid.UUID,
    *,
    llm_goal: Any | None,
    user_message: str,
) -> ResolverResult:
    """
    Decide what to do with the goal signal from this turn.

    Called synchronously inside the chat path — must be fast.
    No extra LLM call is made here.
    """
    # 1. Gate: only life_aim with real intent
    if llm_goal is None:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)
    kind = getattr(llm_goal, "kind", "none")
    if kind != _LIFE_AIM:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)
    intent = (getattr(llm_goal, "intent", None) or "").strip()
    mode = getattr(llm_goal, "mode", None) or "pursuing"
    supersedes = getattr(llm_goal, "supersedes_previous", False)
    if len(intent) < 4:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)

    # 2. Derive type + anchors
    goal_type = _classify_goal_type(intent, {})
    anchors = _extract_anchors_from_intent(intent, goal_type)
    anchors["title"] = intent[:256]

    # 3. Current active goal in this thread
    active_goal = await get_conversation_active_goal(session, conversation_id, person_id)

    # 4. Check if this matches the active goal
    if active_goal is not None and not supersedes:
        full_anchors = {"goal_type": goal_type, **anchors}
        score = _anchor_match_score_from_anchors(active_goal, full_anchors)
        if score >= 0.4:
            # Reinforcing the active goal
            changed = await _update_and_maybe_enqueue(
                session, active_goal, anchors, person_id, activate=False
            )
            return ResolverResult(
                action="reinforce",
                goal=active_goal,
                intelligence_enqueued=changed,
            )

    # 5. Check for a secondary (non-active) existing goal
    full_anchors = {"goal_type": goal_type, **anchors}
    secondary = await find_matching_goal(session, person_id, full_anchors)
    if secondary is not None and (active_goal is None or secondary.id != active_goal.id):
        # Existing secondary goal mentioned
        if supersedes or _is_clear_switch(intent, active_goal):
            # Switch to it
            await activate_goal(session, secondary)
            await switch_conversation_active_goal(session, conversation_id, secondary.id)
            enqueued = await _maybe_enqueue(session, secondary)
            return ResolverResult(action="switch", goal=secondary, intelligence_enqueued=enqueued)
        # Create-secondary path: don't switch active goal
        enqueued = await _maybe_enqueue(session, secondary)
        return ResolverResult(action="create_secondary", goal=secondary, intelligence_enqueued=enqueued)

    # 6. Create new goal
    goal, action = await upsert_goal_from_anchors(
        session,
        person_id,
        goal_type=goal_type,
        title=intent[:256],
        anchors=anchors,
        source_conversation_id=conversation_id,
        activate=supersedes or active_goal is None,
        create_if_new=True,
    )
    if action == "created" and (supersedes or active_goal is None):
        await switch_conversation_active_goal(session, conversation_id, goal.id)

    enqueued_job = await enqueue_goal_intelligence_job(session, goal)
    return ResolverResult(
        action=action,
        goal=goal,
        intelligence_enqueued=enqueued_job is not None,
    )


def _anchor_match_score_from_anchors(goal: Goal, anchors: dict[str, Any]) -> float:
    from pai.services.goals.service import _anchor_match_score

    return _anchor_match_score(goal, anchors)


async def _update_and_maybe_enqueue(
    session: AsyncSession,
    goal: Goal,
    anchors: dict[str, Any],
    person_id: uuid.UUID,
    activate: bool,
) -> bool:
    from pai.services.goals.service import update_goal_anchors, INTEL_STALE

    changed = await update_goal_anchors(session, goal, anchors)
    if changed:
        goal.intelligence_status = INTEL_STALE
        await enqueue_goal_intelligence_job(session, goal)
    return changed


async def _maybe_enqueue(session: AsyncSession, goal: Goal) -> bool:
    from pai.services.goals.service import INTEL_PENDING, INTEL_STALE

    if goal.intelligence_status in (INTEL_PENDING, INTEL_STALE):
        job = await enqueue_goal_intelligence_job(session, goal)
        return job is not None
    return False
