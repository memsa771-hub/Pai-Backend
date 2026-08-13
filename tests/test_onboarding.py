from __future__ import annotations


def test_onboarding_required_before_chat(verified_user):
    client, headers, _ = verified_user
    blocked = client.post("/api/v1/chat", headers=headers, json={"message": "Hello"})
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "ONBOARDING_INCOMPLETE"


def test_onboarding_offers_manual_or_cv_choice(verified_user):
    client, headers, _ = verified_user
    status = client.get("/api/v1/onboarding", headers=headers)
    assert status.status_code == 200, status.text
    body = status.json()["data"]
    assert body["completed"] is False
    assert body["path"] is None
    ids = {c["id"] for c in body["choices"]}
    assert ids == {"manual", "cv"}


def test_manual_onboarding_unlocks_pai(verified_user):
    client, headers, _ = verified_user
    client.post("/api/v1/onboarding/path", headers=headers, json={"path": "manual"})

    step1 = client.put(
        "/api/v1/onboarding/steps/1",
        headers=headers,
        json={
            "dateOfBirth": "2004-03-12",
            "nationality": "Pakistani",
            "currentCountry": "Pakistan",
            "currentCity": "Lahore",
            "currentStatus": "student",
        },
    )
    assert step1.status_code == 200, step1.text
    assert "nationalId" not in step1.json()["data"]["steps"][0]["values"]

    incomplete = client.post("/api/v1/onboarding/complete", headers=headers)
    assert incomplete.status_code == 422

    step2 = client.put(
        "/api/v1/onboarding/steps/2",
        headers=headers,
        json={
            "educationLevel": "bachelor",
            "institution": "Bahria University",
            "degree": "BSCS",
            "major": "Computer Science",
            "gpa": 3.4,
        },
    )
    assert step2.status_code == 200, step2.text

    step3 = client.put(
        "/api/v1/onboarding/steps/3",
        headers=headers,
        json={
            "primaryGoal": "MS Computer Science in Germany",
            "studyCountry": "Germany",
            "intake": "Fall 2027",
            "budget": "limited",
        },
    )
    assert step3.status_code == 200, step3.text
    assert step3.json()["data"]["canComplete"] is True

    done = client.post("/api/v1/onboarding/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["data"]["completed"] is True

    me = client.get("/api/v1/person/me", headers=headers).json()["data"]
    assert me["onboardingCompleted"] is True
    educations = client.get("/api/v1/person/educations", headers=headers).json()["data"]["items"]
    assert educations[0]["institution"] == "Bahria University"
    goals = client.get("/api/v1/person/goals", headers=headers).json()["data"]["items"]
    assert goals[0]["title"] == "MS Computer Science in Germany"


def test_cv_path_asks_only_missing_destination_intake_budget(verified_user):
    """Ali-style: education already known; PAI only asks study country, intake, budget."""
    client, headers, _ = verified_user
    client.post("/api/v1/onboarding/path", headers=headers, json={"path": "cv"})
    client.put(
        "/api/v1/onboarding/steps/2",
        headers=headers,
        json={
            "educationLevel": "bachelor",
            "institution": "Bahria University",
            "degree": "BSCS",
            "major": "Computer Science",
            "gpa": 3.4,
        },
    )
    status = client.get("/api/v1/onboarding", headers=headers).json()["data"]
    assert set(status["missingRequired"]) <= {
        "primaryGoal",
        "studyCountry",
        "intake",
        "budget",
        "institution",
    }
    assert "dateOfBirth" not in status["missingRequired"]
    assert "nationalId" not in status["missingRequired"]

    review = client.post(
        "/api/v1/onboarding/review",
        headers=headers,
        json={
            "studyCountry": "Germany",
            "intake": "Fall 2027",
            "budget": "limited",
            "primaryGoal": "MS CS in Germany",
        },
    )
    assert review.status_code == 200, review.text
    assert review.json()["data"]["canComplete"] is True

    done = client.post("/api/v1/onboarding/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["data"]["completed"] is True
