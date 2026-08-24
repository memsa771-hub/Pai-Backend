"""Goal intelligence pipeline — four stages run sequentially, each isolated.

Research → Assessment → Gaps → Planning → counselor_brief

Design rules:
- Each stage reads structured JSON from the previous stage.
- No stage calls another stage conversationally.
- Stages accept mocked LLM responses in tests (pass fake_llm_response).
- counselor_brief is capped at 10 lines.
- Pipeline failure does not block chat.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from pai.llm.gateway import LLMGateway
from pai.llm.schemas import LLMMessage

logger = logging.getLogger(__name__)

_BRIEF_MAX_LINES = 10


# ── Template configs ──────────────────────────────────────────────────────────

_GOAL_TYPE_GUIDANCE: dict[str, dict[str, str]] = {
    "admission": {
        "research_focus": (
            "university requirements, eligibility rules, IELTS/GRE cutoffs, "
            "application deadlines, scholarship options, tuition range"
        ),
        "assessment_focus": "GPA, test scores, SOP strength, relevant projects, work experience",
        "gaps_focus": "missing test scores, GPA shortfall, missing documents, deadline risks",
    },
    "job": {
        "research_focus": "job market demand, required skills, typical experience level, salary range",
        "assessment_focus": "skills match, work experience, portfolio, communication fit",
        "gaps_focus": "missing skills, portfolio gaps, experience gap, CV weaknesses",
    },
    "internship": {
        "research_focus": "internship availability, required skills, application timelines, stipend range",
        "assessment_focus": "skills, projects, availability, academic standing",
        "gaps_focus": "missing skills, project portfolio, availability mismatch",
    },
    "general": {
        "research_focus": "key requirements, options, typical steps to achieve this goal",
        "assessment_focus": "how well the student's current profile matches the goal",
        "gaps_focus": "missing items, blockers, weaknesses",
    },
}


def _goal_guidance(goal_type: str) -> dict[str, str]:
    return _GOAL_TYPE_GUIDANCE.get(goal_type, _GOAL_TYPE_GUIDANCE["general"])


# ── Stage helpers ─────────────────────────────────────────────────────────────

async def _llm_json(
    gateway: LLMGateway,
    system: str,
    user: str,
    *,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    """Call LLM and parse JSON response. Returns empty dict on failure."""
    try:
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        response = await gateway.run(
            task="goal_intelligence",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        content = getattr(response, "content", None) or ""
        # Strip markdown fences if present
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = "\n".join(stripped.splitlines()[1:])
            if stripped.endswith("```"):
                stripped = stripped[: stripped.rfind("```")]
        return json.loads(stripped.strip())
    except Exception:
        logger.exception("LLM JSON call failed")
        return {}


# ── Stage 1: Research ─────────────────────────────────────────────────────────

async def run_research_stage(
    gateway: LLMGateway,
    *,
    goal_type: str,
    goal_title: str,
    anchors: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce structured requirements, options, eligibility rules, deadlines.

    Input:  goal anchors
    Output: research JSON object
    """
    guidance = _goal_guidance(goal_type)
    system = (
        "You are an expert counselor assistant that produces structured research "
        "about student goals. Return ONLY valid JSON — no prose outside the JSON. "
        "Be concise and factual."
    )
    anchor_str = json.dumps(anchors, ensure_ascii=False)
    user = f"""Goal: {goal_title}
Type: {goal_type}
Anchors: {anchor_str}
Research focus: {guidance['research_focus']}

Return a JSON object with these keys:
- "requirements": list of key requirements (strings)
- "options": list of top 3 realistic options or universities/companies (strings)
- "eligibility_rules": list of eligibility conditions (strings)
- "deadlines": list of relevant deadlines or timelines (strings)
- "typical_cost": string estimate of cost or salary range
- "notes": any important caveats (string)
"""
    result = await _llm_json(gateway, system, user, max_tokens=1200)
    if not result:
        return {
            "requirements": [],
            "options": [],
            "eligibility_rules": [],
            "deadlines": [],
            "typical_cost": "unknown",
            "notes": "Research unavailable.",
            "_error": True,
        }
    return result


# ── Stage 2: Assessment ───────────────────────────────────────────────────────

async def run_assessment_stage(
    gateway: LLMGateway,
    *,
    research: dict[str, Any],
    vault_snapshot: dict[str, Any],
    goal_type: str,
    goal_title: str,
) -> dict[str, Any]:
    """
    Compare user's profile against research output.

    Input:  research JSON + vault snapshot
    Output: assessment JSON
    """
    guidance = _goal_guidance(goal_type)
    system = (
        "You are an expert counselor that assesses how well a student's profile "
        "matches a goal. Return ONLY valid JSON."
    )
    user = f"""Goal: {goal_title}
Type: {goal_type}
Assessment focus: {guidance['assessment_focus']}

Research summary:
{json.dumps(research, ensure_ascii=False, indent=2)}

Student profile:
{json.dumps(vault_snapshot, ensure_ascii=False, indent=2)}

Return a JSON object with these keys:
- "overall_fit": one of "strong" | "moderate" | "weak" | "unknown"
- "strengths": list of student strengths relevant to this goal (strings)
- "weaknesses": list of student weaknesses (strings)
- "meets_requirements": object mapping each requirement to true/false/null
- "notes": brief assessment summary (string, max 3 sentences)
"""
    result = await _llm_json(gateway, system, user, max_tokens=800)
    if not result:
        return {
            "overall_fit": "unknown",
            "strengths": [],
            "weaknesses": [],
            "meets_requirements": {},
            "notes": "Assessment unavailable.",
            "_error": True,
        }
    return result


# ── Stage 3: Gaps ─────────────────────────────────────────────────────────────

async def run_gaps_stage(
    gateway: LLMGateway,
    *,
    assessment: dict[str, Any],
    goal_type: str,
    goal_title: str,
) -> list[dict[str, Any]]:
    """
    Identify missing items for this goal.

    Input:  assessment JSON
    Output: list of gap objects
    """
    guidance = _goal_guidance(goal_type)
    system = (
        "You are an expert counselor that identifies specific gaps a student "
        "must address to achieve their goal. Return ONLY valid JSON."
    )
    user = f"""Goal: {goal_title}
Type: {goal_type}
Gaps focus: {guidance['gaps_focus']}

Assessment:
{json.dumps(assessment, ensure_ascii=False, indent=2)}

Return a JSON object with key "gaps" containing a list.
Each gap object must have:
- "item": what is missing (string)
- "category": one of "test_score" | "document" | "experience" | "skill" | "deadline" | "other"
- "blocking": true if this gap blocks the application, false if it's advisory
- "action": recommended action to close this gap (string)
"""
    result = await _llm_json(gateway, system, user, max_tokens=600)
    gaps = result.get("gaps") if isinstance(result, dict) else None
    if not isinstance(gaps, list):
        return []
    return gaps


# ── Stage 4: Planning ─────────────────────────────────────────────────────────

async def run_planning_stage(
    gateway: LLMGateway,
    *,
    gaps: list[dict[str, Any]],
    research: dict[str, Any],
    goal_type: str,
    goal_title: str,
) -> list[dict[str, Any]]:
    """
    Create an ordered action plan from gaps + research.

    Input:  gaps list + research JSON
    Output: list of plan step objects
    """
    system = (
        "You are an expert counselor that creates concise, ordered action plans "
        "for students. Return ONLY valid JSON."
    )
    user = f"""Goal: {goal_title}
Type: {goal_type}

Gaps:
{json.dumps(gaps, ensure_ascii=False, indent=2)}

Key deadlines/options from research:
{json.dumps(research.get('deadlines', []), ensure_ascii=False)}

Return a JSON object with key "plan" containing an ordered list of steps.
Each step must have:
- "step": concise action description (string, ≤ 120 chars)
- "priority": "high" | "medium" | "low"
- "timeline": rough timeline, e.g. "this week" | "1-2 months" | "before deadline"
- "depends_on": list of step indices (0-based) this step depends on (empty list if none)
"""
    result = await _llm_json(gateway, system, user, max_tokens=800)
    plan = result.get("plan") if isinstance(result, dict) else None
    if not isinstance(plan, list):
        return []
    return plan


# ── Counselor brief ───────────────────────────────────────────────────────────

async def build_counselor_brief(
    gateway: LLMGateway,
    *,
    goal_title: str,
    goal_type: str,
    research: dict[str, Any],
    assessment: dict[str, Any],
    gaps: list[dict[str, Any]],
    plan: list[dict[str, Any]],
) -> str:
    """
    Produce the compact counselor_brief (max 10 lines).
    This is what the counselor reads every turn.
    """
    system = (
        "You produce a concise goal intelligence brief for a counselor. "
        "Maximum 10 lines. Plain text, no markdown headers. "
        "Cover: goal, fit assessment, top 2 gaps, top 3 next steps."
    )
    user = f"""Goal: {goal_title}
Type: {goal_type}

Overall fit: {assessment.get('overall_fit', 'unknown')}
Strengths: {', '.join((assessment.get('strengths') or [])[:3])}
Weaknesses: {', '.join((assessment.get('weaknesses') or [])[:3])}
Blocking gaps: {', '.join(g['item'] for g in gaps if g.get('blocking'))[:3]}
Top plan steps: {', '.join(s['step'] for s in plan[:3])}

Write a 5–10 line counselor brief. Be specific and actionable.
"""
    try:
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        resp = await gateway.run(task="goal_intelligence", messages=messages, max_tokens=300, temperature=0.3)
        brief = getattr(resp, "content", None) or ""
        lines = [ln for ln in (brief or "").splitlines() if ln.strip()]
        return "\n".join(lines[:_BRIEF_MAX_LINES])
    except Exception:
        logger.exception("Failed to build counselor brief")
        fit = assessment.get("overall_fit", "unknown")
        blocking = [g["item"] for g in gaps if g.get("blocking")][:2]
        steps = [s["step"] for s in plan[:3]]
        parts = [f"Goal: {goal_title}", f"Fit: {fit}"]
        if blocking:
            parts.append("Blocking gaps: " + "; ".join(blocking))
        if steps:
            parts.append("Next steps: " + "; ".join(steps))
        return "\n".join(parts[:_BRIEF_MAX_LINES])


# ── Full pipeline ─────────────────────────────────────────────────────────────

async def run_full_pipeline(
    gateway: LLMGateway,
    *,
    goal_type: str,
    goal_title: str,
    anchors: dict[str, Any],
    vault_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """
    Run all 4 stages sequentially and return the full intelligence object.

    Failures in individual stages produce partial output — pipeline continues.
    """
    research = await run_research_stage(
        gateway, goal_type=goal_type, goal_title=goal_title, anchors=anchors
    )
    assessment = await run_assessment_stage(
        gateway,
        research=research,
        vault_snapshot=vault_snapshot,
        goal_type=goal_type,
        goal_title=goal_title,
    )
    gaps = await run_gaps_stage(
        gateway, assessment=assessment, goal_type=goal_type, goal_title=goal_title
    )
    plan = await run_planning_stage(
        gateway, gaps=gaps, research=research, goal_type=goal_type, goal_title=goal_title
    )
    brief = await build_counselor_brief(
        gateway,
        goal_title=goal_title,
        goal_type=goal_type,
        research=research,
        assessment=assessment,
        gaps=gaps,
        plan=plan,
    )
    any_error = any(
        (isinstance(s, dict) and s.get("_error"))
        for s in [research, assessment]
    )
    status = "partial" if any_error else "ready"
    return {
        "research": research,
        "assessment": assessment,
        "gaps": gaps,
        "plan": plan,
        "counselor_brief": brief,
        "status": status,
        "freshness": {
            "computed_at": datetime.now(UTC).isoformat(),
        },
    }
