from __future__ import annotations


def test_onboarding_required_before_chat(verified_user):
    client, headers, _ = verified_user
    blocked = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "Hello"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "ONBOARDING_INCOMPLETE"


def test_onboarding_three_steps_write_vault_and_unlock(verified_user):
    client, headers, _ = verified_user

    status = client.get("/api/v1/onboarding", headers=headers)
    assert status.status_code == 200, status.text
    body = status.json()["data"]
    assert body["completed"] is False
    assert body["currentStep"] == 1
    assert body["totalSteps"] == 3

    step1 = client.put(
        "/api/v1/onboarding/steps/1",
        headers=headers,
        json={
            "fullName": "Ayesha Khan",
            "dateOfBirth": "2004-03-12",
            "gender": "female",
            "nationality": "Pakistani",
        },
    )
    assert step1.status_code == 200, step1.text
    assert step1.json()["data"]["steps"][0]["complete"] is True
    assert step1.json()["data"]["currentStep"] == 2

    incomplete = client.post("/api/v1/onboarding/complete", headers=headers)
    assert incomplete.status_code == 422

    step2 = client.put(
        "/api/v1/onboarding/steps/2",
        headers=headers,
        json={
            "currentCountry": "Pakistan",
            "currentCity": "Lahore",
            "currentStatus": "student",
            "linkedinUrl": "linkedin.com/in/ayesha-khan",
        },
    )
    assert step2.status_code == 200, step2.text
    assert step2.json()["data"]["steps"][1]["complete"] is True
    assert step2.json()["data"]["steps"][1]["values"]["linkedinUrl"].startswith("https://")

    step3 = client.put(
        "/api/v1/onboarding/steps/3",
        headers=headers,
        json={
            "educationLevel": "high_school",
            "institution": "Punjab College",
            "major": "Pre-Engineering",
            "graduationYear": 2022,
        },
    )
    assert step3.status_code == 200, step3.text
    assert step3.json()["data"]["canComplete"] is True

    done = client.post("/api/v1/onboarding/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["data"]["completed"] is True

    me = client.get("/api/v1/person/me", headers=headers).json()["data"]
    assert me["fullName"] == "Ayesha Khan"
    assert me["onboardingCompleted"] is True

    educations = client.get("/api/v1/person/educations", headers=headers).json()["data"]["items"]
    assert educations[0]["institution"] == "Punjab College"
    assert educations[0]["degree"] == "High School"

    city = client.get("/api/v1/vault/fields/location.current_city", headers=headers)
    assert city.json()["data"]["value"] == "Lahore"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "vault-user@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["onboardingCompleted"] is True

    again = client.post("/api/v1/onboarding/complete", headers=headers)
    assert again.status_code == 200
    assert again.json()["data"]["completed"] is True


def test_onboarding_skips_optional_fields(verified_user):
    client, headers, _ = verified_user
    client.put(
        "/api/v1/onboarding/steps/1",
        headers=headers,
        json={
            "fullName": "Ali Raza",
            "dateOfBirth": "2003-01-01",
            "gender": "male",
            "nationality": "Pakistani",
        },
    )
    skipped = client.put(
        "/api/v1/onboarding/steps/2",
        headers=headers,
        json={
            "currentCountry": "Pakistan",
            "currentCity": "Karachi",
            "currentStatus": "professional",
        },
    )
    assert skipped.status_code == 200
    values = skipped.json()["data"]["steps"][1]["values"]
    assert values["nationalId"] is None
    assert values["linkedinUrl"] is None


def test_onboarding_rejects_invalid_linkedin(verified_user):
    client, headers, _ = verified_user
    resp = client.put(
        "/api/v1/onboarding/steps/2",
        headers=headers,
        json={
            "currentCountry": "Pakistan",
            "currentCity": "Lahore",
            "currentStatus": "student",
            "linkedinUrl": "https://example.com/not-linkedin",
        },
    )
    assert resp.status_code == 422
