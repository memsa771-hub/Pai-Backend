from __future__ import annotations

import pytest
from conftest import ONBOARDING_PAYLOAD
from pydantic import ValidationError

from pai.onboarding.enums import field_enum_catalog
from pai.onboarding.schema import OnboardingSubmit


def test_enum_catalog_exposes_dropdown_ids():
    catalog = field_enum_catalog()
    assert {item["id"] for item in catalog["primaryGoal"]} == {
        "exploring",
        "placement",
        "admission",
        "professional",
        "journey_tracker",
    }
    assert any(item["id"] == "PK" for item in catalog["currentCountry"])
    assert len(catalog["currentCountry"]) > 200
    assert "phd" in {item["id"] for item in catalog["educationLevel"]}
    assert "fully_funded" in {item["id"] for item in catalog["budget"]}



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
        "gender",
        "primaryGoal",
    ):
        assert field in names
    assert "institution" not in names
    assert "degree" not in names


def test_submit_schema_optional_fields_can_be_omitted():
    body = OnboardingSubmit.model_validate(ONBOARDING_PAYLOAD)
    assert body.linkedinUrl is None
    assert body.skills == []
    assert body.workExperience == []
    assert body.testScores == []


def test_submit_schema_minimal_criticals_are_enough():
    body = OnboardingSubmit.model_validate(
        {
            "phone": "+923001234567",
            "dateOfBirth": "2004-03-12",
            "nationality": "PK",
            "currentCountry": "PK",
            "currentCity": "Lahore",
            "currentStatus": "student",
            "gender": "male",
            "educationLevel": "bachelor",
            "primaryGoal": "admission",
        }
    )
    assert body.institution is None
    assert body.degree is None
    assert body.gpa is None


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


def test_submit_schema_rejects_vague_primary_goal():
    payload = {**ONBOARDING_PAYLOAD, "primaryGoal": "MS Computer Science in Germany"}
    with pytest.raises(ValidationError):
        OnboardingSubmit.model_validate(payload)


def test_submit_schema_accepts_country_name_alias():
    payload = {**ONBOARDING_PAYLOAD, "nationality": "Pakistan", "currentCountry": "Germany"}
    body = OnboardingSubmit.model_validate(payload)
    assert body.nationality == "PK"
    assert body.currentCountry == "DE"
    uk = OnboardingSubmit.model_validate({**ONBOARDING_PAYLOAD, "currentCountry": "UK"})
    assert uk.currentCountry == "GB"
    alpha3 = OnboardingSubmit.model_validate({**ONBOARDING_PAYLOAD, "currentCountry": "DEU"})
    assert alpha3.currentCountry == "DE"
    turkey = OnboardingSubmit.model_validate({**ONBOARDING_PAYLOAD, "currentCountry": "Turkey"})
    assert turkey.currentCountry == "TR"


def test_submit_schema_rejects_unknown_country():
    with pytest.raises(ValidationError, match="ISO 3166-1"):
        OnboardingSubmit.model_validate({**ONBOARDING_PAYLOAD, "currentCountry": "Narnia"})


def test_submit_schema_normalizes_phone_to_e164():
    body = OnboardingSubmit.model_validate(
        {**ONBOARDING_PAYLOAD, "phone": "0300 1234567", "currentCountry": "PK"}
    )
    assert body.phone == "+923001234567"
    with pytest.raises(ValidationError, match="phone"):
        OnboardingSubmit.model_validate({**ONBOARDING_PAYLOAD, "phone": "12345"})




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
    assert "gender" in body["requiredFields"]
    assert "primaryGoal" in body["requiredFields"]
    assert "institution" not in body["requiredFields"]
    assert "institution" in body["conditionalFields"]
    assert "linkedinUrl" in body["optionalFields"]
    goal_ids = {item["id"] for item in body["enums"]["primaryGoal"]}
    assert goal_ids == {
        "exploring",
        "placement",
        "admission",
        "professional",
        "journey_tracker",
    }
    assert any(item["id"] == "PK" for item in body["enums"]["currentCountry"])
    assert {item["id"] for item in body["enums"]["educationLevel"]} >= {
        "high_school",
        "diploma",
        "bachelor",
        "master",
        "phd",
        "other",
    }
    assert "nationalId" not in body["requiredFields"]
    assert body["vaultEnrichment"] == "chat_and_documents"
    assert "starting profile" in body["purpose"].lower() or "lightweight" in body["purpose"].lower()


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
