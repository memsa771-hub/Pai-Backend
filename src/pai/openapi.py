"""OpenAPI / Swagger presentation — DX only; does not weaken auth."""

from __future__ import annotations

from typing import Any

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Liveness and readiness probes (no auth).",
    },
    {
        "name": "auth",
        "description": (
            "Sign up, login, refresh, and account recovery. "
            "**Start here for Swagger testing:** `POST /auth/login` → copy `data.accessToken` → Authorize."
        ),
    },
    {
        "name": "account",
        "description": "Destructive account operations (authenticated).",
    },
    {
        "name": "person",
        "description": "Student identity + typed profile resources (education, skills, goals, …).",
    },
    {
        "name": "onboarding",
        "description": (
            "Required three-step Person Vault setup after first verified login. "
            "Chat and documents stay locked until `POST /api/v1/onboarding/complete`."
        ),
    },
    {
        "name": "vault",
        "description": (
            "Person Vault. Prefer **`GET /api/v1/vault/status`** for a simple filled/missing view "
            "after chat. Other vault routes remain for advanced field CRUD."
        ),
    },
    {
        "name": "chat",
        "description": (
            "Primary PAI counselor entrypoint. "
            "`POST /api/v1/chat` creates or continues a conversation in one call."
        ),
    },
    {
        "name": "conversations",
        "description": (
            "Prefer **`GET /api/v1/conversations/threads`** for full Q&A flows. "
            "CRUD and raw messages endpoints remain available."
        ),
    },
    {
        "name": "documents",
        "description": "Private document upload, extraction jobs, and human review.",
    },
]

API_DESCRIPTION = """
## Placement AI (PAI) API

Persistent student counselor: **Person Vault** (structured truth) + conversation + semantic memory.
Agents reason; deterministic services write trusted data. LLM provider is replaceable (DeepSeek today).

---

### Swagger quick start (local testing)

1. Call **`POST /api/v1/auth/login`** with a **verified** email/password.
2. Copy **`data.accessToken`** only (the long `eyJ…` string).
3. Click **Authorize** (top right) → paste the token **without** the word `Bearer`.
4. Swagger adds `Bearer` for you. Adding it twice causes `401`.
5. Call **`GET /api/v1/auth/me`** — must return 200 before chat.
6. If `data.onboardingCompleted` is false, complete **`GET /api/v1/onboarding`** then steps 1–3 and **`POST /api/v1/onboarding/complete`**.
7. Call **`POST /api/v1/chat`** with a message.

Login auto-bootstraps the Person Vault for verified users. New users must finish onboarding before counselor chat.

### Auth model

| Credential | Where | Purpose |
|------------|--------|---------|
| Access token | `Authorization: Bearer <token>` | API calls (short-lived) |
| Refresh token | HttpOnly cookie `pai_refresh_token` | Silent refresh |
| CSRF | Cookie + `X-CSRF-Token` header | Required on refresh/logout |

Never put secrets in query strings. Never commit real tokens.

### Envelope

Success: `{ "success": true, "data": { … } }`  
Error: `{ "success": false, "error": { "code": "…", "message": "…" } }`
""".strip()


BEARER_DESCRIPTION = (
    "Paste **only** `data.accessToken` from `POST /api/v1/auth/login` "
    "(the `eyJ…` JWT). Do **not** type the word Bearer — Swagger adds it automatically."
)


def customize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    components = schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})

    # Normalize FastAPI's auto-generated bearer scheme for clearer Swagger UX.
    for key, value in list(schemes.items()):
        if not isinstance(value, dict):
            continue
        if value.get("type") == "http" and str(value.get("scheme", "")).lower() == "bearer":
            value["bearerFormat"] = "JWT"
            value["description"] = BEARER_DESCRIPTION
            # Prefer a stable name in the UI.
            if key != "BearerAuth":
                schemes["BearerAuth"] = value
                # Keep old key pointing at same for refs already generated
            break

    if "BearerAuth" in schemes:
        schema["security"] = [{"BearerAuth": []}]

    # Public routes should not require a lock in the global security sense —
    # FastAPI still marks individual ops via dependencies; global security is a hint.
    # Clear global and rely on per-operation security from HTTPBearer dependencies.
    # Actually setting global security makes ALL ops need auth including login — bad.
    schema.pop("security", None)

    return schema
