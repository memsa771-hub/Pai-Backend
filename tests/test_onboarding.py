from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import ONBOARDING_PAYLOAD
from pai.onboarding.schema import OnboardingSubmit


def test_submit_schema_requires_critical_fields():
    with pytest.raises(ValidationError) as exc:
        OnboardingSubmit.model_validate({"nationality": "Pakistani"})
    names = {error["loc"][-1] for error in exc.value.errors()}
    for field in (
        "phone",
        "dateOfBirth",
        "currentCountry",
        "currentCity",
        "currentStatus",
        "educationLevel",
        "institution",
        "primaryGoal",
    ):
        assert field in names


def test_submit_schema_optional_fields_can_be_omitted():
    body = OnboardingSubmit.model_validate(ONBOARDING_PAYLOAD)
    assert body.gender is None
    assert body.linkedinUrl is None
    assert body.skills == []
    assert body.workExperience == []
    assert body.testScores == []


def test_submit_schema_high_school_does_not_need_degree():
    payload = {
        **ONBOARDING_PAYLOAD,
        "educationLevel": "high_school",
        "institution": "City School",
        "degree": None,
        "major": None,
    }
    body = OnboardingSubmit.model_validate(payload)
    assert body.resolved_degree() == "High School"


def test_submit_schema_bachelor_needs_degree_or_field():
    payload = {
        **ONBOARDING_PAYLOAD,
        "educationLevel": "bachelor",
        "degree": None,
        "major": None,
    }
    with pytest.raises(ValidationError, match="degree or field"):
        OnboardingSubmit.model_validate(payload)



def test_onboarding_required_before_chat(verified_user):
    client, headers, _ = verified_user
    blocked = client.post("/api/v1/chat", headers=headers, json={"message": "Hello"})
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "ONBOARDING_INCOMPLETE"


def test_login_does_not_complete_onboarding(verified_user):
    client, headers, _ = verified_user
    status = client.get("/api/v1/onboarding", headers=headers)
    assert status.status_code == 200, status.text
    body = status.json()["data"]
    assert body["completed"] is False
    assert body["onboardingCompleted"] is False
    assert body["nextPath"] == "/onboarding"
    me = client.get("/api/v1/person/me", headers=headers).json()["data"]
    assert me["onboardingCompleted"] is False


def test_onboarding_offers_manual_or_cv_choice(verified_user):
    client, headers, _ = verified_user
    status = client.get("/api/v1/onboarding", headers=headers)
    assert status.status_code == 200, status.text
    body = status.json()["data"]
    assert body["completed"] is False
    assert body["path"] is None
    ids = {c["id"] for c in body["choices"]}
    assert ids == {"manual", "cv"}
    assert "phone" in body["requiredFields"]
    assert "primaryGoal" in body["requiredFields"]
    assert "gender" in body["optionalFields"]
    assert "linkedinUrl" in body["optionalFields"]
    assert "nationalId" not in body["requiredFields"]


def test_incomplete_submit_is_rejected(verified_user):
    client, headers, _ = verified_user
    incomplete = client.post(
        "/api/v1/onboarding",
        headers=headers,
        json={"path": "manual", "nationality": "Pakistani"},
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["error"]["code"] == "VALIDATION_ERROR"
    status = client.get("/api/v1/onboarding", headers=headers).json()["data"]
    assert status["completed"] is False
    assert status["onboardingCompleted"] is False


def test_manual_onboarding_unlocks_pai(verified_user):
    client, headers, _ = verified_user
    done = client.post("/api/v1/onboarding", headers=headers, json=ONBOARDING_PAYLOAD)
    assert done.status_code == 200, done.text
    data = done.json()["data"]
    assert data["completed"] is True
    assert data["onboardingCompleted"] is True
    assert data["nextPath"] != "/onboarding"
    assert data["path"] == "manual"
    assert "nationalId" not in (data.get("values") or {})

    me = client.get("/api/v1/person/me", headers=headers).json()["data"]
    assert me["onboardingCompleted"] is True
    assert me["phone"] == "+923001234567"
    educations = client.get("/api/v1/person/educations", headers=headers).json()["data"]["items"]
    assert educations[0]["institution"] == "Bahria University"
    goals = client.get("/api/v1/person/goals", headers=headers).json()["data"]["items"]
    assert goals[0]["title"] == "MS Computer Science in Germany"


def test_onboarding_submit_is_idempotent(verified_user):
    client, headers, _ = verified_user
    first = client.post("/api/v1/onboarding", headers=headers, json=ONBOARDING_PAYLOAD)
    assert first.status_code == 200, first.text
    completed_at = first.json()["data"]["onboardingCompletedAt"]
    again = client.post("/api/v1/onboarding", headers=headers, json=ONBOARDING_PAYLOAD)
    assert again.status_code == 200, again.text
    data = again.json()["data"]
    assert data["completed"] is True
    assert data["onboardingCompletedAt"] == completed_at
    educations = client.get("/api/v1/person/educations", headers=headers).json()["data"]["items"]
    assert len(educations) == 1


def test_cv_path_completes_only_after_confirmed_payload(verified_user):
    client, headers, _ = verified_user
    payload = {**ONBOARDING_PAYLOAD, "path": "cv"}
    status = client.get("/api/v1/onboarding", headers=headers).json()["data"]
    assert status["completed"] is False
    assert "phone" in status["missingRequired"]
    assert "dateOfBirth" in status["missingRequired"]
    assert "primaryGoal" in status["missingRequired"]

    done = client.post("/api/v1/onboarding", headers=headers, json=payload)
    assert done.status_code == 200, done.text
    data = done.json()["data"]
    assert data["completed"] is True
    assert data["path"] == "cv"
    assert data["onboardingCompleted"] is True
