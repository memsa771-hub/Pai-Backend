# Placement AI — Auth Service (Developer Handoff)

Short guide for engineers joining the project. **Phase 1 only:** authentication. No Person Vault, RAG, documents, or PAI orchestration yet.

## What this repo is

A **standalone FastAPI backend** that exposes stable REST APIs for signup, login, sessions, email verification, and password flows.

- **Frontend / mobile** call **only** this service (`/api/v1/...`).
- **Supabase Auth** handles passwords, tokens, email, and user storage (`auth.users`).
- Supabase is hidden behind an **`AuthProvider`** interface so the identity backend can be replaced later without changing public routes.

```
┌─────────────┐     HTTPS      ┌──────────────────┐     HTTPS      ┌─────────────┐
│   Frontend  │ ────────────► │  PAI Auth Service │ ────────────► │ Supabase    │
│  (any app)  │  /api/v1/auth │  (this repo)      │  /auth/v1/*  │ Auth + DB   │
└─────────────┘               └──────────────────┘               └─────────────┘
```

## Repository layout

```text
src/auth_service/
  app.py              # FastAPI app, middleware, health, lifespan
  config.py           # Pydantic settings from .env
  schemas.py          # Request/response models (Swagger)
  dependencies.py     # JWT validation, CSRF, AuthService injection
  api/auth.py         # HTTP routes
  core/
    provider.py       # AuthProvider protocol (swap point)
    service.py        # Provider-agnostic business logic
    errors.py         # AuthError + codes
  providers/
    supabase.py       # Supabase GoTrue HTTP client
tests/                # API + provider unit tests
```

## Public API (v1)

Base URL example: `http://127.0.0.1:8000`

| Method | Path | Auth | Notes |
|--------|------|------|--------|
| POST | `/api/v1/auth/signup` | — | Creates user in Supabase; may require email confirm |
| POST | `/api/v1/auth/login` | — | Returns `accessToken`; sets cookies |
| POST | `/api/v1/auth/refresh` | Cookie + CSRF | New access token |
| POST | `/api/v1/auth/logout` | Bearer + Cookie + CSRF | Revokes refresh |
| POST | `/api/v1/auth/email-verification/request` | — | Resend verify email |
| POST | `/api/v1/auth/email-verification/confirm` | — | Body: `code` (token) + `email` |
| POST | `/api/v1/auth/password/forgot` | — | Generic success message |
| POST | `/api/v1/auth/password/reset` | — | Body: `ticket` + `newPassword` |
| POST | `/api/v1/auth/password/change` | Bearer | Clears session cookies |
| GET | `/api/v1/auth/me` | Bearer | Current user profile |
| DELETE | `/api/v1/account` | Bearer | Deletes user (service role on server) |
| GET | `/health/live` | — | Process up |
| GET | `/health/ready` | — | Supabase Auth reachable |

Interactive docs: **`/docs`** (Swagger).

### Response shape (always)

Success:

```json
{ "success": true, "data": { } }
```

Error:

```json
{
  "success": false,
  "error": { "code": "INVALID_CREDENTIALS", "message": "..." }
}
```

Common `error.code` values: `INVALID_CREDENTIALS`, `EMAIL_NOT_VERIFIED`, `EMAIL_ALREADY_IN_USE`, `INVALID_TOKEN`, `CSRF_FAILED`, `VALIDATION_ERROR`, `PROVIDER_UNAVAILABLE`.

## How the frontend should integrate

### Access token

- Returned in JSON on login, refresh, and email confirm.
- Send on protected routes: `Authorization: Bearer <accessToken>`.
- Validated locally with `SUPABASE_JWT_SECRET` (`sub` = user id).

### Refresh token + CSRF

- **`pai_refresh_token`** — HttpOnly, Secure (in prod), SameSite (env).
- **`pai_csrf_token`** — readable by JS.
- On **`POST /refresh`** and **`POST /logout`**: send cookie **and** header `X-CSRF-Token: <same as csrf cookie>`.

### Email verification (important)

Supabase emails contain a link like:

`https://<project>.supabase.co/auth/v1/verify?token=...&type=signup&redirect_to=...`

**Do not rely on redirect to `localhost:3000` unless the frontend is running.**

Recommended UX:

1. User signs up → `POST /signup`.
2. User opens email → app extracts `token` from the link.
3. App calls `POST /email-verification/confirm` with:

```json
{
  "code": "<token from email>",
  "email": "<same email as signup>"
}
```

4. App stores `accessToken` and cookies from response → user can call `/me`.

Verification tokens are **single-use** and **time-limited**; use the **latest** email after resend.

### Password reset

- `POST /password/forgot` with `{ "email" }`.
- User gets email with recovery token → `POST /password/reset` with `{ "ticket": "<token>", "newPassword": "..." }`.

## Local setup

1. Copy env files:
   - `.env.example` → `.env`
   - Optional worksheet: `supabase-setup.template.env`
2. Fill Supabase values from **Dashboard → Project Settings → API**:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
3. Supabase **Authentication → URL Configuration**: allow redirect URLs matching `.env`.
4. Install and run:

```bash
pip install -e ".[dev]"
# or with uv:
uv sync
uv run alembic upgrade head
uv run uvicorn auth_service.app:create_app_from_env --factory --reload --host 127.0.0.1 --port 8000
```

Set `DATABASE_URL` and `VAULT_ENCRYPTION_KEY` in `.env` (see `.env.example`).

On **Windows**, use Supabase **Session pooler** (IPv4), not the direct `db.*` host. In Dashboard → **Connect** → **Session**, copy the URI, URL-encode the password, and set `postgresql+asyncpg://...`.

```powershell
uv sync
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue   # if you exported an old URL
uv run alembic upgrade head
# or: .\scripts\migrate.ps1
```

5. Verify: `GET /health/ready` → `"status":"ready"`.

### Tests & lint

```bash
python -m ruff format src tests
python -m ruff check src tests
python -m pytest
```

Phase 2 integration tests (`tests/test_person_vault.py`) require PostgreSQL. Start `docker compose` or set `TEST_DATABASE_URL`, then run `alembic upgrade head` before pytest.

### Docker

```bash
docker build -t pai-auth-service .
docker run --env-file .env -p 8000:8000 pai-auth-service
```

## Security notes (implemented)

- No custom password hashing or refresh-token tables in this service.
- Passwords and tokens are not logged.
- Refresh tokens only in HttpOnly cookies; access token in JSON.
- CSRF on refresh/logout.
- CORS and trusted hosts from environment.
- Account delete uses **service role** only on the server — never expose it to the client.

## Phase 2 — Person Profile & Person Vault

After verified login or email confirmation, the service **attempts** Person + Vault bootstrap (failures are logged; auth still succeeds). Recovery: `POST /api/v1/person/bootstrap` (idempotent).

Identity in app DB: `auth_provider=supabase`, `external_auth_id` = JWT `sub`. Never accept `person_id` / `vault_id` / `external_auth_id` in request bodies.

### Person & Vault routes

| Method | Path |
|--------|------|
| POST | `/api/v1/person/bootstrap` |
| GET/PATCH | `/api/v1/person/me` |
| CRUD | `/api/v1/person/educations`, `work-experiences`, `projects`, `skills`, `certifications`, `goals` |
| GET | `/api/v1/vault`, `/catalog`, `/completion`, `/missing` |
| GET/PATCH/DELETE | `/api/v1/vault/fields/{field_key}` |
| GET | `/api/v1/vault/fields/{field_key}/history` |

Sensitive vault fields: masked unless `includeSensitive=true` (owner only). Fernet key: `VAULT_ENCRYPTION_KEY`.

### Account deletion order

Authenticate → soft-delete/anonymize Person + Vault data → delete Supabase user. If provider deletion fails after app cleanup, API returns `ACCOUNT_DELETE_INCOMPLETE` (support must finish provider deletion).

### Storage model

- **Typed tables:** persons, educations, work_experiences, projects, skills, certifications, goals  
- **Sparse:** `vault_values` only when a flexible catalog field has a value  
- **Catalog:** `src/auth_service/vault/catalog.py` (C/I/E priorities, scopes, storage mapping)

## What is **not** built yet (Phase 3+)

- OAuth (Google, etc.) on public routes
- MFA
- Rate limiting at the API layer
- Chat, AI extraction, documents, memory, RAG, pgvector, LangGraph
- LinkedIn / university portal import
- Re-auth before account deletion

Supabase may support OAuth/MFA; wiring them would be new routes + `AuthProvider` methods.

## Changing auth or database later

- **Easy:** New clients, same `/api/v1` contract.
- **Moderate:** New `AuthProvider` implementation (e.g. not Supabase) + env config.
- **Hard:** Migrating **existing users** to another provider (export/import or forced re-signup).

App data uses Supabase user **`id`** (`sub` in JWT) via `persons.external_auth_id`. Postgres is required for Phase 2 profile/vault features.

## Key files to read first

1. `src/auth_service/api/auth.py` — routes and cookies  
2. `src/auth_service/core/provider.py` — provider contract  
3. `src/auth_service/providers/supabase.py` — Supabase HTTP mapping  
4. `tests/test_auth_api.py` — expected HTTP behaviour  

## Questions / ownership

- **Secrets:** `.env` only on developer machines / CI; never commit.
- **Production:** set `COOKIE_SECURE=true`, tight `CORS_ORIGINS`, HTTPS reverse proxy.
- Full env reference: [`.env.example`](.env.example). Extended ops notes: [`README.md`](README.md).
