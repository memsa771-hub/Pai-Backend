def _signup_body(email: str, **overrides) -> dict:
    body = {
        "fullName": "Ali Khan",
        "email": email,
        "phone": "+923001234567",
        "password": "Password123!",
        "confirmPassword": "Password123!",
    }
    body.update(overrides)
    return body


def test_signup_flow(client, fake_provider):
    response = client.post(
        "/api/v1/auth/signup",
        json=_signup_body("new@example.com"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "verify" in body["data"]["message"].lower()
    assert body["data"].get("session") is None


def test_verification_and_login(client, fake_provider):
    client.post(
        "/api/v1/auth/signup",
        json=_signup_body("verify@example.com"),
    )
    confirm = client.post(
        "/api/v1/auth/email-verification/confirm",
        json={"code": "ticket:verify@example.com", "email": "verify@example.com"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["success"] is True
    assert "pai_refresh_token" in confirm.cookies

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["accessToken"]
    assert login.cookies.get("pai_refresh_token")
    assert login.cookies.get("pai_csrf_token")


def test_login_unverified(client, fake_provider):
    fake_provider.users["blocked@example.com"] = {
        "id": "blocked",
        "email": "blocked@example.com",
        "password": "Password123!",
        "verified": False,
    }
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "blocked@example.com", "password": "Password123!"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_login_generic_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_refresh_and_logout_cookies(client, fake_provider, bearer_token):
    fake_provider.users["refresh@example.com"] = {
        "id": "user-refresh",
        "email": "refresh@example.com",
        "password": "Password123!",
        "verified": True,
    }
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "Password123!"},
    )
    refresh_cookie = login.cookies.get("pai_refresh_token")
    csrf = login.cookies.get("pai_csrf_token")

    missing_csrf = client.post(
        "/api/v1/auth/refresh", cookies={"pai_refresh_token": refresh_cookie}
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_FAILED"

    refreshed = client.post(
        "/api/v1/auth/refresh",
        cookies={"pai_refresh_token": refresh_cookie, "pai_csrf_token": csrf},
        headers={"X-CSRF-Token": csrf},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["accessToken"]

    access = refreshed.json()["data"]["accessToken"]
    logout = client.post(
        "/api/v1/auth/logout",
        cookies={
            "pai_refresh_token": refreshed.cookies.get("pai_refresh_token"),
            "pai_csrf_token": csrf,
        },
        headers={"Authorization": f"Bearer {access}", "X-CSRF-Token": csrf},
    )
    assert logout.status_code == 200
    assert fake_provider.logout_calls


def test_forgot_and_reset_password(client, fake_provider):
    fake_provider.users["reset@example.com"] = {
        "id": "reset-user",
        "email": "reset@example.com",
        "password": "Password123!",
        "verified": True,
    }
    forgot = client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "reset@example.com"},
    )
    assert forgot.status_code == 200
    assert "If an account exists" in forgot.json()["data"]["message"]

    reset = client.post(
        "/api/v1/auth/password/reset",
        json={
            "ticket": "passwordReset:reset@example.com",
            "newPassword": "NewPassword123!",
            "confirmPassword": "NewPassword123!",
        },
    )
    assert reset.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "NewPassword123!"},
    )
    assert login.status_code == 200


def test_change_password(client, fake_provider):
    fake_provider.users["change@example.com"] = {
        "id": "user-1",
        "email": "change@example.com",
        "password": "Password123!",
        "verified": True,
    }
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "change@example.com", "password": "Password123!"},
    )
    token = login.json()["data"]["accessToken"]

    response = client.post(
        "/api/v1/auth/password/change",
        json={"newPassword": "Changed123!", "confirmPassword": "Changed123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert fake_provider.users["change@example.com"]["password"] == "Changed123!"
    assert response.cookies.get("pai_refresh_token") is None


def test_me_and_delete_account(client, fake_provider):
    fake_provider.users["me@example.com"] = {
        "id": "user-1",
        "email": "me@example.com",
        "password": "Password123!",
        "verified": True,
    }
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "Password123!"},
    )
    token = login.json()["data"]["accessToken"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "me@example.com"

    deleted = client.delete("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert deleted.status_code == 200
    assert fake_provider.deleted == ["user-1"]


def test_signup_duplicate_email(client, fake_provider):
    client.post("/api/v1/auth/signup", json=_signup_body("dup@example.com"))
    again = client.post("/api/v1/auth/signup", json=_signup_body("dup@example.com"))
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "EMAIL_ALREADY_IN_USE"


def test_signup_password_mismatch(client):
    response = client.post(
        "/api/v1/auth/signup",
        json=_signup_body("mismatch@example.com", confirmPassword="Password123?"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_signup_requires_name_and_phone(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "x@example.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        },
    )
    assert response.status_code == 422


def test_reset_password_mismatch(client):
    response = client.post(
        "/api/v1/auth/password/reset",
        json={
            "ticket": "passwordReset:x@example.com",
            "newPassword": "NewPassword123!",
            "confirmPassword": "OtherPassword123!",
        },
    )
    assert response.status_code == 422


def test_resend_verification(client):
    response = client.post(
        "/api/v1/auth/email-verification/request",
        json={"email": "any@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_health_endpoints(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 200
