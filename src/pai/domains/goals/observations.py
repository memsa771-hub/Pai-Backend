"""Compatibility for grounded career observations; all goal writes stay here."""
from pai.domains.goals.service import INTEL_PENDING, INTEL_STALE, enqueue_goal_intelligence_job, upsert_goal_from_anchors
from pai.domains.goals.types import GoalType, GoalWriteAction

async def submit_career_interest(session, person_id, candidate):
    title = candidate.value if isinstance(candidate.value, str) else str(candidate.value)
    goal, action = await upsert_goal_from_anchors(
        session, person_id, goal_type=GoalType.GENERAL.value, title=title,
        anchors={"title": title[:256]}, activate=True, create_if_new=True,
    )
    if goal is None:
        return "rejected"
    if action != GoalWriteAction.REINFORCE or goal.intelligence_status in (INTEL_PENDING, INTEL_STALE):
        await enqueue_goal_intelligence_job(session, goal)
    return action
