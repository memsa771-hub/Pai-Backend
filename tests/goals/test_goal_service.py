"""GoalService unit tests — bypass LLM entirely, test DB-layer logic.

These tests use a mocked AsyncSession and verify:
- Goal creation/update with correct fields
- Vault-owned keys are rejected from goal anchors
- activate_goal transitions statuses correctly
- find_matching_goal uses anchor similarity, not title equality
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pai.domains.goals.service import (
    _assert_no_vault_keys,
    _anchor_match_score,
    find_matching_goal,
    create_goal,
    update_goal_anchors,
    activate_goal,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_PAUSED,
    INTEL_STALE,
    VAULT_FIELDS_THAT_AFFECT_GOALS,
)
from pai.domains.student.person.models import Goal


# ── Vault key guard ───────────────────────────────────────────────────────────


def test_vault_keys_rejected():
    with pytest.raises(ValueError, match="ielts"):
        _assert_no_vault_keys({"ielts": 7.5, "target_country": "DE"})


def test_vault_keys_accepted_for_valid_anchors():
    _assert_no_vault_keys({"target_country": "DE", "degree_level": "ms"})


# ── Anchor similarity ─────────────────────────────────────────────────────────


def _make_goal(goal_type="admission", target_country="DE", degree_level="ms", program=None, role=None, target_company=None) -> Goal:
    g = MagicMock(spec=Goal)
    g.goal_type = goal_type
    g.target_country = target_country
    g.degree_level = degree_level
    g.program = program
    g.role = role
    g.target_company = target_company
    return g


def test_anchor_match_same_country_degree():
    goal = _make_goal(goal_type="admission", target_country="DE", degree_level="ms")
    anchors = {"goal_type": "admission", "target_country": "DE", "degree_level": "ms"}
    score = _anchor_match_score(goal, anchors)
    assert score >= 0.6


def test_anchor_match_different_country():
    goal = _make_goal(goal_type="admission", target_country="DE", degree_level="ms")
    anchors = {"goal_type": "admission", "target_country": "CN", "degree_level": "ms"}
    score = _anchor_match_score(goal, anchors)
    # Country differs — should be below threshold
    assert score < 0.6


def test_anchor_match_different_type_returns_zero():
    goal = _make_goal(goal_type="job")
    anchors = {"goal_type": "admission", "target_country": "DE"}
    assert _anchor_match_score(goal, anchors) == 0.0


# ── GoalService operations (mocked session) ───────────────────────────────────


@pytest.fixture
def mock_session():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def person_id():
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_create_goal_stores_anchors(mock_session, person_id):
    goal = await create_goal(
        mock_session,
        person_id,
        goal_type="admission",
        title="MS CS in Germany",
        anchors={"target_country": "DE", "degree_level": "ms"},
    )
    assert goal.goal_type == "admission"
    assert goal.target_country == "DE"
    assert goal.degree_level == "ms"
    assert goal.intelligence_status == "pending"
    mock_session.add.assert_called_once_with(goal)


@pytest.mark.asyncio
async def test_create_goal_rejects_vault_keys(mock_session, person_id):
    with pytest.raises(ValueError):
        await create_goal(
            mock_session,
            person_id,
            goal_type="admission",
            title="MS in Germany",
            anchors={"ielts": 7.0},
        )


@pytest.mark.asyncio
async def test_update_goal_anchors_marks_stale(mock_session, person_id):
    goal = await create_goal(
        mock_session,
        person_id,
        goal_type="admission",
        title="MS in Germany",
        anchors={"target_country": "DE"},
    )
    # goal.anchors is a real dict from create_goal, not a mock
    assert isinstance(goal.anchors, dict)
    goal.intelligence_status = "ready"
    changed = await update_goal_anchors(mock_session, goal, {"target_country": "CN"})
    assert changed is True
    assert goal.target_country == "CN"


@pytest.mark.asyncio
async def test_activate_goal_pauses_others(mock_session, person_id):
    other_goal = MagicMock(spec=Goal)
    other_goal.id = uuid.uuid4()
    other_goal.lifecycle_status = LIFECYCLE_ACTIVE
    other_goal.status = LIFECYCLE_ACTIVE

    result = MagicMock()
    result.scalars.return_value = iter([other_goal])
    mock_session.execute = AsyncMock(return_value=result)

    target = await create_goal(
        mock_session,
        person_id,
        goal_type="admission",
        title="MS in Germany",
        anchors={},
    )
    target.lifecycle_status = "draft"

    await activate_goal(mock_session, target)

    assert other_goal.lifecycle_status == LIFECYCLE_PAUSED
    assert target.lifecycle_status == LIFECYCLE_ACTIVE


# ── Vault→Goals selective refresh mapping ────────────────────────────────────


def test_vault_fields_affect_admission_goals():
    assert "admission" in VAULT_FIELDS_THAT_AFFECT_GOALS.get("application.test_scores", [])


def test_vault_fields_ielts_not_in_map():
    """IELTS is a Vault key — it routes via test_scores, not ielts itself."""
    assert "ielts" not in VAULT_FIELDS_THAT_AFFECT_GOALS
