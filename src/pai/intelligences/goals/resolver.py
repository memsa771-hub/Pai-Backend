"""Goal resolver — cheap, synchronous, no extra LLM call on the chat path.

Decision logic:
  1. GoalExtract from fact extraction (already computed) tells us kind/intent/mode.
  2. Only life_aim with confidence signals trigger goal writes.
  3. University / title containment reinforces an existing goal (no duplicate).
  4. Return action: create | create_secondary | switch | reinforce | none
  5. create_secondary = second goal without changing active_goal_id.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pai.domains.goals.service import (
    activate_goal,
    enqueue_goal_intelligence_job,
    find_matching_goal,
    get_conversation_active_goal,
    list_goals,
    upsert_goal_from_anchors,
)
from pai.domains.goals.models import Goal

logger = logging.getLogger(__name__)

_LIFE_AIM = "life_aim"

# Phrases that mean "continue this pursuit", not "mint a new goal"
_FOCUS_PREFIX = re.compile(
    r"^(?:i\s+want\s+to\s+)?(?:focus\s+on|getting\s+into|get\s+into|apply\s+to|"
    r"applying\s+to|aiming\s+(?:for|to)|looking\s+at)\s+",
    re.IGNORECASE,
)


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
    if any(
        kw in lower
        for kw in (
            "ms ",
            "msc",
            "bachelor",
            "phd",
            "mba",
            "masters",
            "degree",
            "university",
            "admission",
        )
    ):
        return "admission"
    if any(kw in lower for kw in ("internship", "intern")):
        return "internship"
    if any(
        kw in lower
        for kw in (
            "job",
            "swe",
            "engineer",
            "developer",
            "analyst",
            "role",
            "position",
            "full-time",
        )
    ):
        return "job"
    return "general"


def _extract_anchors_from_intent(intent: str, goal_type: str) -> dict[str, Any]:
    """Best-effort anchor extraction from intent string (no LLM)."""
    anchors: dict[str, Any] = {"goal_type": goal_type}
    lower = intent.casefold()

    country_map = {
        "germany": "DE",
        "china": "CN",
        "canada": "CA",
        "uk": "GB",
        "usa": "US",
        "australia": "AU",
        "dubai": "AE",
        "uae": "AE",
        "sweden": "SE",
        "netherlands": "NL",
        "france": "FR",
        "turkey": "TR",
        "singapore": "SG",
        "malaysia": "MY",
        "new zealand": "NZ",
        "italy": "IT",
    }
    for name, code in country_map.items():
        if name in lower:
            anchors["target_country"] = code
            break

    if goal_type == "admission":
        if re.search(r"\bphd\b|\bdoctor", lower):
            anchors["degree_level"] = "phd"
        elif re.search(r"\bms\b|m\.s|msc|masters?\b", lower):
            anchors["degree_level"] = "ms"
        elif re.search(r"\bbs\b|b\.s|bachelor", lower):
            anchors["degree_level"] = "bs"
        elif re.search(r"\bmba\b", lower):
            anchors["degree_level"] = "mba"

    prog_map = {
        "cs": "computer science",
        "computer science": "computer science",
        "ai": "artificial intelligence",
        "ml": "machine learning",
        "data science": "data science",
        "electrical engineering": "electrical engineering",
        "mechanical engineering": "mechanical engineering",
    }
    for kw, prog in prog_map.items():
        if kw in lower:
            anchors["program"] = prog
            break

    return anchors


def _goal_name_tokens(goal: Goal) -> list[str]:
    """Tokens that identify this goal for containment matching."""
    tokens: list[str] = []
    title = (goal.title or "").casefold().strip()
    if title:
        tokens.append(title)
        # Significant words from title (drop stopwords)
        for word in re.findall(r"[a-z0-9]{3,}", title):
            if word not in {"the", "and", "for", "into", "get", "getting", "want", "admission"}:
                tokens.append(word)
    for uni in (goal.anchors or {}).get("target_universities") or []:
        if isinstance(uni, str) and uni.strip():
            tokens.append(uni.casefold().strip())
    if goal.target_country:
        tokens.append(str(goal.target_country).casefold())
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen and len(t) >= 3:
            seen.add(t)
            out.append(t)
    return out


def _text_mentions_goal(text: str, goal: Goal) -> bool:
    """True if intent/message clearly refers to this existing goal (uni/title)."""
    hay = (text or "").casefold()
    if not hay:
        return False
    title = (goal.title or "").casefold().strip()
    if title and (title in hay or hay in title):
        return True
    # Strip focus-style prefixes then compare remainder to title
    stripped = _FOCUS_PREFIX.sub("", hay).strip(" .")
    if title and stripped and (stripped in title or title in stripped):
        return True
    for uni in (goal.anchors or {}).get("target_universities") or []:
        if isinstance(uni, str) and uni.casefold().strip() and uni.casefold() in hay:
            return True
    # Distinctive multi-word / proper-name tokens from title (e.g. bologna, hust, tum)
    for token in _goal_name_tokens(goal):
        if len(token) >= 4 and token in hay:
            return True
    return False


def _is_clear_switch(
    new_intent: str,
    active_goal: Goal | None,
) -> bool:
    """Return True when the message clearly references a *different* pursuit."""
    if active_goal is None:
        return False
    if _text_mentions_goal(new_intent, active_goal):
        return False
    from pai.domains.goals.service import _anchor_match_score

    new_anchors = _extract_anchors_from_intent(new_intent, active_goal.goal_type)
    score = _anchor_match_score(active_goal, new_anchors)
    return score < 0.4


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
    if llm_goal is None:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)
    kind = getattr(llm_goal, "kind", "none")
    if kind != _LIFE_AIM:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)
    intent = (getattr(llm_goal, "intent", None) or "").strip()
    supersedes = getattr(llm_goal, "supersedes_previous", False)
    if len(intent) < 4:
        return ResolverResult(action="none", goal=None, intelligence_enqueued=False)

    match_text = f"{intent} {user_message or ''}"
    goal_type = _classify_goal_type(intent, {})
    anchors = _extract_anchors_from_intent(intent, goal_type)
    anchors["title"] = intent[:256]

    active_goal = await get_conversation_active_goal(session, conversation_id, person_id)

    # 0. University / title containment against active goal (prevents "focus on Bologna" dupes)
    if active_goal is not None and not supersedes and _text_mentions_goal(match_text, active_goal):
        await activate_goal(session, active_goal, conversation_id=conversation_id)
        changed = await _update_and_maybe_enqueue(
            session, active_goal, anchors, person_id, activate=False
        )
        return ResolverResult(
            action="reinforce",
            goal=active_goal,
            intelligence_enqueued=changed,
        )

    # 1. Anchor similarity against active goal
    if active_goal is not None and not supersedes:
        full_anchors = {"goal_type": goal_type, **anchors}
        score = _anchor_match_score_from_anchors(active_goal, full_anchors)
        if score >= 0.4:
            changed = await _update_and_maybe_enqueue(
                session, active_goal, anchors, person_id, activate=False
            )
            return ResolverResult(
                action="reinforce",
                goal=active_goal,
                intelligence_enqueued=changed,
            )

    # 2. Containment against any existing non-archived goal
    all_goals = await list_goals(session, person_id, include_archived=False)
    mentioned = next((g for g in all_goals if _text_mentions_goal(match_text, g)), None)
    if mentioned is not None and not supersedes:
        if active_goal is None or mentioned.id == active_goal.id:
            await activate_goal(session, mentioned, conversation_id=conversation_id)
            enqueued = await _maybe_enqueue(session, mentioned)
            return ResolverResult(
                action="reinforce", goal=mentioned, intelligence_enqueued=enqueued
            )
        # Mentioned a different existing goal → switch when clear, else secondary
        if _is_clear_switch(intent, active_goal) or supersedes:
            await activate_goal(session, mentioned, conversation_id=conversation_id)
            enqueued = await _maybe_enqueue(session, mentioned)
            return ResolverResult(
                action="switch", goal=mentioned, intelligence_enqueued=enqueued
            )
        enqueued = await _maybe_enqueue(session, mentioned)
        return ResolverResult(
            action="create_secondary", goal=mentioned, intelligence_enqueued=enqueued
        )

    # 3. Anchor match against other goals
    full_anchors = {"goal_type": goal_type, **anchors}
    secondary = await find_matching_goal(session, person_id, full_anchors)
    if secondary is not None and (active_goal is None or secondary.id != active_goal.id):
        if supersedes or _is_clear_switch(intent, active_goal):
            await activate_goal(session, secondary, conversation_id=conversation_id)
            enqueued = await _maybe_enqueue(session, secondary)
            return ResolverResult(
                action="switch", goal=secondary, intelligence_enqueued=enqueued
            )
        enqueued = await _maybe_enqueue(session, secondary)
        return ResolverResult(
            action="create_secondary", goal=secondary, intelligence_enqueued=enqueued
        )

    # 4. Create new goal
    should_activate = supersedes or active_goal is None
    goal, action = await upsert_goal_from_anchors(
        session,
        person_id,
        goal_type=goal_type,
        title=intent[:256],
        anchors=anchors,
        source_conversation_id=conversation_id,
        activate=should_activate,
        create_if_new=True,
    )
    enqueued_job = await enqueue_goal_intelligence_job(session, goal)
    return ResolverResult(
        action=action,
        goal=goal,
        intelligence_enqueued=enqueued_job is not None,
    )


def _anchor_match_score_from_anchors(goal: Goal, anchors: dict[str, Any]) -> float:
    from pai.domains.goals.service import _anchor_match_score

    return _anchor_match_score(goal, anchors)


async def _update_and_maybe_enqueue(
    session: AsyncSession,
    goal: Goal,
    anchors: dict[str, Any],
    person_id: uuid.UUID,
    activate: bool,
) -> bool:
    from pai.domains.goals.service import INTEL_STALE, update_goal_anchors

    del person_id, activate
    changed = await update_goal_anchors(session, goal, anchors)
    if changed:
        goal.intelligence_status = INTEL_STALE
        await enqueue_goal_intelligence_job(session, goal)
    return changed


async def _maybe_enqueue(session: AsyncSession, goal: Goal) -> bool:
    from pai.domains.goals.service import INTEL_PENDING, INTEL_STALE

    if goal.intelligence_status in (INTEL_PENDING, INTEL_STALE):
        job = await enqueue_goal_intelligence_job(session, goal)
        return job is not None
    return False
