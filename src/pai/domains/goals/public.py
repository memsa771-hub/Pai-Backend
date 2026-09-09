"""Goal-owned projections for the combined profile UI."""
from sqlalchemy import func, select
from pai.domains.goals.models import Goal


async def profile_records(session, person_id, *, limit=20):
    rows = (await session.execute(select(Goal).where(Goal.person_id == person_id).order_by(Goal.updated_at.desc()).limit(limit))).scalars()
    return [{"id": str(row.id), "goalType": row.goal_type, "title": row.title,
             "description": row.description, "status": row.status, "priority": row.priority}
            for row in rows]


async def count_goals(session, person_id):
    return int(await session.scalar(select(func.count()).select_from(Goal).where(Goal.person_id == person_id)) or 0)


class GoalService:
    def __init__(self, session):
        self.session = session

    async def observe_turn(self, person_id, **turn):
        from pai.intelligences.goals.resolver import resolve
        from pai.domains.goals.service import goal_to_public
        result = await resolve(self.session, person_id=person_id, **turn)
        return {"action": result.action, "goal": goal_to_public(result.goal),
                "intelligence_enqueued": result.intelligence_enqueued}

    async def get_active_goal(self, person_id):
        from pai.domains.goals.service import get_active_goal, goal_to_public
        return goal_to_public(await get_active_goal(self.session, person_id))

    async def get_briefing(self, person_id):
        from pai.domains.goals.service import get_active_goal, get_goal_intelligence
        goal = await get_active_goal(self.session, person_id)
        if goal is None:
            return None
        intel = await get_goal_intelligence(self.session, goal.id)
        return {"goal_id": str(goal.id), "status": goal.intelligence_status,
                "brief": intel.counselor_brief if intel else None}
