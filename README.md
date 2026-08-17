# Placement AI (PAI) Backend

FastAPI backend for **Placement AI**: auth, Person Vault, chat counselor, Vault Intelligence extraction, documents, and memory. The frontend calls this service only; Supabase Auth stays behind an `AuthProvider` interface.

**Detailed handoff:** [DEVELOPER.md](DEVELOPER.md)

## Stack

- Python 3.12+
- FastAPI, httpx, Pydantic Settings
- Supabase Auth (GoTrue)
- PostgreSQL (Supabase-hosted or compatible) — SQLAlchemy 2 async, Alembic
- **uv** (recommended) or pip for installs

## Quick start

```bash
cp .env.example .env
# Fill Supabase API keys + DATABASE_URL + VAULT_ENCRYPTION_KEY (see below)
```

### With uv (recommended)

```powershell
cd PAI-main-b-end
uv sync
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
uv run alembic upgrade head
uv run uvicorn pai.app:create_app_from_env --factory --reload --host 127.0.0.1 --port 8000
```

Or run migrations only:

```powershell
.\scripts\migrate.ps1
```

### With pip

```bash
pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn pai.app:create_app_from_env --factory --reload
```

Open Swagger: `http://localhost:8000/docs`

---

## PostgreSQL on Supabase (required for Phase 2)

Phase 2 stores **Person**, **Vault**, and profile data in **your Supabase Postgres** (`public` schema). Verified users in **Authentication → Users** do **not** appear in `persons` until **bootstrap** runs (login, email confirm, or `POST /api/v1/person/bootstrap`).

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | App DB — use **`postgresql+asyncpg://...`** (not plain `postgresql://`) |
| `VAULT_ENCRYPTION_KEY` | Fernet key for sensitive vault fields ([generate](https://cryptography.io/en/latest/fernet/)) |
| `SUPABASE_*` | Auth API (see `.env.example`) |

**Password in URL:** URL-encode special characters (`@` → `%40`, `<` → `%3C`, `>` → `%3E`).

Use the **database password** from Supabase (Database settings), **not** the anon or service_role API keys.

### How to set `DATABASE_URL` correctly

1. Supabase Dashboard → your project → **Connect** (top) → **Connection string**.
2. Choose **URI** and **Session pooler** (port **5432**).
3. Do **not** use **Direct** connection on Windows for local dev if you see DNS errors (see troubleshooting).
4. Copy the URI. It should look like:

   ```text
   postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-SOME-REGION.pooler.supabase.com:5432/postgres
   ```

5. Convert for this app:

   ```text
   postgresql+asyncpg://postgres.YOUR_PROJECT_REF:URL_ENCODED_PASSWORD@aws-0-SOME-REGION.pooler.supabase.com:5432/postgres
   ```

6. Paste into `.env` as `DATABASE_URL`.

7. If unsure about the password: **Project Settings → Database → Reset database password**, then update `.env`.

### Run migrations

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
uv run alembic upgrade head
```

Alembic reads `DATABASE_URL` from **`.env`** via app settings. A stale `DATABASE_URL` in your **PowerShell session** overrides `.env` and causes confusing errors — clear it before migrating.

After success, tables such as `persons`, `person_vaults`, `vault_values`, etc. appear in **Table Editor** or SQL:

```sql
SELECT id, email, email_verified, external_auth_id, created_at
FROM persons
WHERE deleted_at IS NULL;
```

---

## Database connection troubleshooting

### `Can't load plugin: sqlalchemy.dialects:driver`

Alembic was using the placeholder URL from `alembic.ini` instead of `.env`. Fixed in this repo — ensure `DATABASE_URL` is set in `.env` and run `uv run alembic upgrade head` again.

### `getaddrinfo failed` for `db.PROJECT_REF.supabase.co`

Supabase **Direct** host is often **IPv6-only**. Many Windows setups cannot resolve/connect to it.

**Fix:** Use **Session pooler** URI from **Connect** (IPv4), not the Direct `db.*.supabase.co` host.

### `tenant/user postgres.PROJECT_REF not found`

You reached a pooler, but the **host/region does not match your project** (e.g. guessing `aws-0-ap-south-1` when your project uses another region).

**Fix:**

1. Copy the **exact** pooler hostname from **Connect → Session pooler** (do not guess the region).
2. User must be `postgres.YOUR_PROJECT_REF` as shown in the dashboard.
3. Reset database password if needed and URL-encode it in `DATABASE_URL`.
4. Clear shell `DATABASE_URL` and re-run migrations.

### Verified auth users but empty `persons` table

Bootstrap never succeeded (DB down, wrong `DATABASE_URL`, or migrations not applied). After DB is fixed: log in or call `POST /api/v1/person/bootstrap` with a verified user’s Bearer token.

### Workaround without local DB connectivity

Apply the SQL from `alembic/versions/001_phase2_person_vault.py` (`upgrade()`) in Supabase **SQL Editor**. Prefer fixing `DATABASE_URL` so `uv run alembic upgrade head` works for future migrations.

---

## API overview

### Auth (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/signup` | Register (`fullName`, `email`, `password`, `confirmPassword`). Duplicate email returns `409 EMAIL_ALREADY_IN_USE`. |
| POST | `/api/v1/auth/login` | Login; cookies + Person bootstrap; returns `onboardingCompleted` and `nextPath` |
| POST | `/api/v1/auth/session` | Exchange email-redirect tokens for a PAI session (cookies + bootstrap + `nextPath`) |
| POST | `/api/v1/auth/refresh` | Refresh (CSRF + cookie) |
| POST | `/api/v1/auth/logout` | Logout |
| POST | `/api/v1/auth/email-verification/*` | Resend or confirm email (OTP / `token_hash`) |
| POST | `/api/v1/auth/password/*` | Password flows |
| GET | `/api/v1/auth/me` | Supabase user + onboarding flag (Bearer) |
| DELETE | `/api/v1/account` | Delete auth user + app data |

### Onboarding (lightweight seed after first verified login)

Onboarding is **not** the main way to fill the Person Vault. It collects a small reliable starting profile so PAI can advise from the first chat. Deeper student intelligence is built over time from **chat fact extraction**, **CV/document extraction**, and later updates to the same Vault.

After verified login, the user chooses **Complete Onboarding** (form) or **Upload My CV**. The form is one `POST /api/v1/onboarding`. The CV path is one `POST /api/v1/onboarding/cv` — extract fills the Vault and **marks onboarding complete**. Chat stays locked until one of those succeeds (`onboardingCompleted`).

Signup and login **never** mark onboarding complete.

**Form path required fields:** phone (E.164 via `phonenumbers` — send `+923001234567` or a national number with `currentCountry`), date of birth, nationality and current country (ISO 3166-1 via `pycountry` — send `PK` or `Pakistan`), gender, current city, current status, education level, primary goal (`exploring` | `placement` | `admission` | `professional` | `journey_tracker`).

The **CV path does not require those fields.** Anything the CV omitted is filled later in chat.

Conditional (send if known): institution, degree, field of study (`major` enum).

Optional: goal detail (free-text note), LinkedIn, GPA, graduation year, skills, work experience, target countries (ISO), study country (ISO), intake season + year, budget band, test scores, scholarships.

`GET /api/v1/onboarding` (before complete) returns `enums` — use those ids in the submit payload, not free-text labels. Country dropdowns bind to `enums.countries`. `POST` returns compact status only.

Field-by-field reference (including `otherLevelLabel`): [docs/onboarding-fields.md](docs/onboarding-fields.md).

National ID is **not** part of general onboarding. Name and email come from signup.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/onboarding` | Incomplete: form catalog. Complete: compact status. |
| POST | `/api/v1/onboarding` | Form path: submit starting profile; compact status. Idempotent. |
| POST | `/api/v1/onboarding/cv` | CV path: extract, mark complete, compact status. |

### Person & Vault (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/person/bootstrap` | Idempotent Person + Vault setup |
| GET/PATCH | `/api/v1/person/me` | Profile |
| CRUD | `/api/v1/person/educations`, `work-experiences`, … | Typed profile |
| GET | `/api/v1/vault` | Whole vault: filled + empty + still required, typed records, completion |
| GET | `/api/v1/vault/catalog` | Field schema (not this student's values) |
| PATCH/DELETE | `/api/v1/vault/fields/{field_key}` | Set or clear one sparse field |
| GET | `/api/v1/vault/fields/{field_key}/history` | Change log for that field |

### Counselor & documents (PAI)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Send a counselor message (one thread per student) |
| GET | `/api/v1/chat/messages` | Paginated transcript (omit offset = latest page) |
| POST/GET/DELETE | `/api/v1/documents` | Upload & list private documents |
| GET | `/api/v1/documents/{id}/status`, `/candidates` | Processing & extracted candidates |
| POST | `/api/v1/documents/{id}/review`, `/reprocess` | Human review & re-queue |

Configure `DEEPSEEK_API_KEY`, optional `TAVILY_API_KEY` for live web search, LLM model env vars, and `SUPABASE_STORAGE_BUCKET`. Set `ENABLE_DOCUMENT_WORKER=true` in production to process uploads in the background.

### Health

| GET | `/health/live` | Liveness |
| GET | `/health/ready` | Supabase Auth reachable |

Success: `{ "success": true, "data": {} }`  
Error: `{ "success": false, "error": { "code", "message" } }`

Session: access token in JSON (`Authorization: Bearer`); refresh in HttpOnly `pai_refresh_token`; CSRF on refresh/logout.

---

## Supabase Auth setup

1. [supabase.com/dashboard](https://supabase.com/dashboard) — create project.
2. **Project Settings → API** — `SUPABASE_URL`, anon key, service_role key, JWT secret → `.env`.
3. **Authentication → Providers → Email** — enable Email; **Confirm email: ON**.
4. **Authentication → URL Configuration**
   - Site URL: `http://localhost:3000` (production frontend origin later).
   - Redirect URLs (exact match):
     - `http://localhost:3000/auth/verify-email`
     - `http://localhost:3000/auth/reset-password`
     - production copies of those paths
5. PAI `.env` must use the **same** callback URLs (`EMAIL_VERIFICATION_REDIRECT_URL`, `PASSWORD_RESET_REDIRECT_URL`) and list that origin in `CORS_ORIGINS`. FastAPI Cloud needs the same env vars.
6. Optional: **SMTP** for production email.

### After the user clicks “verify email”

Supabase verifies the address and redirects to `/auth/verify-email` with tokens in the **URL hash** (`#access_token=…&refresh_token=…&type=signup`). The frontend should:

1. Read the hash on a client page (the hash is never sent to a server).
2. `POST /api/v1/auth/session` with `{ accessToken, refreshToken }` (`credentials: "include"`).
3. Clear the hash (`history.replaceState`).
4. Route to `data.nextPath` — `/onboarding` until onboarding is complete, then `/`.

Do not keep tokens in the URL or in `localStorage`. PAI stores the refresh token in an HttpOnly cookie and bootstraps the Person Vault on this call.

Worksheet: `supabase-setup.template.env`

---

## Development

```bash
uv sync
uv run ruff format src tests
uv run ruff check src tests
uv run pytest
```

Phase 2 tests need a working Postgres (`DATABASE_URL`); they skip if the DB is unavailable.

Apply Phase 3 tables after Phase 2:

```bash
uv run alembic upgrade head
```

Migrations: `001_phase2_person_vault`, `002_phase3_counselor` (conversations, messages, orchestration_runs, documents, document_jobs, document_candidates).

## Docker (API only)

```bash
docker build -t pai-backend .
docker run --env-file .env -p 8000:8000 pai-backend
```

## Out of scope (Phase 4+)

Long-term memory, pgvector/RAG, opportunity databases, admissions/internship agents, CV/SOP generation, email/application submission.

## Security notes

- Never commit `.env` or expose `SUPABASE_SERVICE_ROLE_KEY`, `DEEPSEEK_API_KEY`, or DB passwords.
- Rotate credentials if they were shared in chat or logs.
- Production: `COOKIE_SECURE=true`, tight `CORS_ORIGINS`, HTTPS.
