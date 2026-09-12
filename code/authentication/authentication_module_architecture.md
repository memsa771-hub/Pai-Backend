# PAI Authentication System: Architecture and Engineering Reference

Last verified against the `monolith-v2` source tree: 2026-09-12.

This is the canonical engineering map for authentication in PAI. Supabase Auth owns identities,
credentials, password hashing, email verification, recovery proofs, and refresh-token rotation.
PAI owns HTTP policy, session cookies, CSRF checks, JWT verification, abuse limits, local student
profile provisioning, onboarding access gates, and account-data cleanup.

## 1. Runtime design

```text
Browser or mobile client
  -> RequestLimitsMiddleware (body size, origin policy, anonymous/IP limit)
  -> FastAPI auth route and Pydantic request validation
  -> account/action limiter
  -> AuthService
  -> SupabaseAuthProvider over a pooled async HTTP client
  -> Supabase GoTrue

Successful login or verification
  -> return short-lived access token in JSON
  -> store rotating refresh token in HttpOnly cookie
  -> store CSRF token in readable SameSite cookie
  -> bounded local Person lookup/provisioning
```

The access token is sent as `Authorization: Bearer <token>` on protected API requests. The refresh
token is never returned in response JSON. JavaScript reads the CSRF cookie and mirrors it into the
`X-CSRF-Token` header only for refresh/logout requests that use the refresh cookie.

CAPTCHA is deliberately absent from the current API contract. Do not send `captchaToken` and do
not enable CAPTCHA in Supabase until a frontend challenge and backend verification are introduced
together.

## 2. Development and production behavior

| Concern | Development with no Redis | Development with Redis | Production |
| --- | --- | --- | --- |
| Rate-limit backend | Atomic in-process buckets | Redis Lua reservation | Shared Redis required |
| Added network trip | None | One Redis trip | One Redis trip |
| Multiple API processes | Each has independent counters | Shared counters | Shared counters |
| Limiter outage policy | Not applicable | Configurable | Fail closed |
| Cookies | HTTP allowed | HTTP allowed | Secure HTTPS required |
| Allowed origins | CORS plus API same-origin | Same | Explicit HTTPS origins |
| Startup validation | Developer-friendly | Developer-friendly | Rejects insecure configuration |

The in-process limiter exists only for a single local development server. It prevents accidental
retry floods without making login depend on Redis or a remote PostgreSQL call. Production settings
validation requires `ENABLE_RATE_LIMITS=true`, `AUTH_RATE_LIMIT_FAIL_CLOSED=true`, and a non-empty
`RATE_LIMIT_REDIS_URL`.

For production-like local testing:

```powershell
docker compose up -d redis
```

```dotenv
RATE_LIMIT_REDIS_URL=redis://127.0.0.1:6379/0
ENABLE_RATE_LIMITS=true
AUTH_RATE_LIMIT_FAIL_CLOSED=true
```

## 3. Public endpoint contract

Base path: `/api/v1/auth` except account deletion.

| Method and path | Request | Authentication | Result |
| --- | --- | --- | --- |
| `POST /signup` | `fullName`, `email`, `password`, `confirmPassword` | Public | Generic 201; sends verification email |
| `POST /login` | `email`, `password` | Public | Access token, user/profile state, refresh and CSRF cookies |
| `POST /refresh` | Empty body | Refresh cookie + CSRF cookie/header + trusted origin | Rotated tokens; stable CSRF token |
| `POST /logout` | Empty body | CSRF when refresh cookie exists; bearer optional | Provider revocation and cleared cookies |
| `POST /email-verification/request` | `email` | Public | Enumeration-safe generic response |
| `POST /email-verification/confirm` | `code`, `email`, optional `verifier` | Public | Session after OTP, hash, or PKCE proof |
| `POST /session` | `accessToken`, `refreshToken` | Valid matching token pair | Cookie-backed PAI session |
| `POST /password/forgot` | `email` | Public | Enumeration-safe generic response |
| `POST /password/reset` | Recovery proof and new password pair | Fresh recovery proof | Password reset; cookies cleared |
| `POST /password/change` | New password pair | Bearer with recent authentication | Password changed; sign-in required |
| `GET /me` | None | Valid bearer token | Supabase user and local onboarding state |
| `DELETE /api/v1/account` | None | Bearer with recent authentication | Local anonymization, then identity deletion |

Login request:

```json
{
  "email": "user@example.com",
  "password": "Str0ngPass#1"
}
```

Refresh request:

```http
POST /api/v1/auth/refresh
Cookie: pai_refresh_token=...; pai_csrf_token=...
Origin: https://app.example.com
X-CSRF-Token: <same value as pai_csrf_token>
```

Successful session responses use this shape:

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "accessTokenExpiresIn": 3600,
    "user": {
      "id": "provider-user-id",
      "email": "user@example.com",
      "emailVerified": true,
      "displayName": "User",
      "avatarUrl": null,
      "roles": ["authenticated"],
      "createdAt": "..."
    },
    "profilePending": false,
    "onboardingCompleted": false,
    "nextPath": "/onboarding"
  }
}
```

## 4. Login latency path

Login performs only these blocking operations:

1. One IP limit reservation and one account limit reservation. With no local Redis, both are
   in-memory; with Redis, each is a bounded Redis operation.
2. One pooled HTTP request to Supabase `/token?grant_type=password`.
3. One bounded local `Person` lookup. Its deadline is `AUTH_PROFILE_TIMEOUT_SECONDS`; if the
   profile database is slow, authentication still succeeds with `profilePending=true`.

There is no Supabase admin lookup and no CAPTCHA call. Existing-user login does not lock or rewrite
the local profile. The frontend should show the authenticated shell immediately, then call `/me`
when `profilePending=true` rather than holding the login screen.

Do not retry login automatically after an ambiguous timeout. Show a retry action. Refresh requests
should be deduplicated client-side so multiple tabs do not rotate the same cookie concurrently.

## 5. Tokens, cookies, and CSRF

- Access tokens are locally verified for signature, issuer, audience, expiry, issued-at time,
  subject, role, and allowed algorithm.
- Asymmetric `ES256`/`RS256` keys come from Supabase JWKS and are cached with concurrency-safe
  refresh. `HS256` is a legacy option and can be disabled.
- Refresh tokens live in an `HttpOnly` cookie, use the configured `SameSite` policy, and require
  `Secure` in production.
- The CSRF cookie is readable by the frontend and must equal `X-CSRF-Token` using a constant-time
  comparison.
- Browser origins must be configured in `CORS_ORIGINS`; Swagger and clients served from the API
  are allowed by exact scheme/host same-origin matching.
- Auth responses use `Cache-Control: no-store`.
- Password change and account deletion require a recent password/OTP/recovery authentication event;
  refreshing an old session does not make it recent.

## 6. Enumeration and failure behavior

Signup, resend-verification, and forgot-password return generic messages so callers cannot reliably
discover whether an email is registered. Login collapses unknown-user and wrong-password failures
to `INVALID_CREDENTIALS`.

| Code | HTTP | Client behavior |
| --- | ---: | --- |
| `INVALID_CREDENTIALS` | 401 | Show one generic email/password error |
| `INVALID_TOKEN` | 401 | Try refresh once; otherwise sign in |
| `EMAIL_NOT_VERIFIED` | 403 | Offer resend verification |
| `CSRF_FAILED` | 403 | Re-establish session; verify origin and token pairing |
| `REAUTHENTICATION_REQUIRED` | 403 | Ask user to sign in, then resume sensitive action |
| `ONBOARDING_INCOMPLETE` | 403 | Route to `nextPath` |
| `AUTH_RATE_LIMITED` / `USAGE_LIMIT` | 429 | Respect `Retry-After` |
| `PROVIDER_UNAVAILABLE` | 503 | Show temporary failure and manual retry |
| `LIMITS_UNAVAILABLE` | 503 | Production limiter unavailable; do not bypass it |
| `ACCOUNT_UNAVAILABLE` | 403 | End the session and contact support if unexpected |

## 7. File-by-file reference

### Application wiring and configuration

- `src/pai/app.py`: creates FastAPI, installs request-limit middleware, creates the shared Supabase
  provider and JWT verifier, exposes health/readiness, registers routers, and closes clients.
- `src/pai/config.py`: authentication, cookie, redirect, HTTP-pool, JWT, Redis, and limit settings.
  Production validation rejects insecure cookies, wildcard origins/hosts, HTTP authentication URLs,
  missing Redis, disabled auth limits, and unsafe legacy signing configuration.
- `.env.example`: configuration inventory without credentials.
- `docker-compose.yml`: local Redis and PostgreSQL services.

### HTTP interface

- `src/pai/interfaces/api/auth.py`: auth/account routes, cookie lifecycle, session responses, bounded
  profile lookup, verification/recovery, `/me`, password change, and deletion.
- `src/pai/interfaces/api/schemas.py`: request/response validation, password-pair checks, humanized
  validation errors, and Swagger models. CAPTCHA is absent here.
- `src/pai/interfaces/api/dependencies.py`: bearer extraction, JWT verification, DB sessions, Person
  resolution, onboarding/recent-login gates, CSRF checks, and account limits.
- `src/pai/interfaces/api/openapi.py`: bearer-auth OpenAPI and Swagger guidance.
- `src/pai/interfaces/api/__init__.py`: router registration.

### Identity provider and cryptography

- `src/pai/platform/security/auth/provider.py`: provider-neutral protocol and identity/session result
  data classes.
- `src/pai/platform/security/auth/service.py`: normalized business facade, enumeration-resistant
  responses, error collapsing, refresh/logout recovery, token-pair matching, and CSRF generation.
- `src/pai/platform/security/auth/supabase.py`: GoTrue REST implementation, pooled/bounded HTTP,
  header construction, error translation, token parsing, recovery, user mutation, health, and
  service-role identity deletion.
- `src/pai/platform/security/auth/jwt.py`: strict JWT verification, algorithm allowlist,
  issuer/audience/claim checks, asynchronous JWKS cache, and recent-auth enforcement.
- `src/pai/platform/security/origin.py`: configured-origin and exact API same-origin checks.

### Abuse, availability, and latency controls

- `src/pai/platform/request_limits.py`: ASGI body size, browser origin, anonymous/IP limits, and
  no-store response headers.
- `src/pai/platform/limits.py`: common reservation interface; local atomic buckets outside production
  when Redis is absent, and shared Redis when configured.
- `src/pai/platform/redis_limits.py`: atomic multi-key Redis Lua reservation, hashed subjects, TTLs,
  bounded connections, and shutdown.
- `src/pai/platform/bounded_io.py`: deadlines and concurrency budgets for slow operations.
- `src/pai/platform/latency.py`: named timing spans used by login.
- `src/pai/platform/operations.py`: readiness checks for Supabase, database, migrations, workers,
  and Redis when configured.

### Local identity and access state

- `src/pai/domains/student/person/models.py`: canonical `Person`, provider identity link, account,
  verification, and onboarding state.
- `src/pai/domains/student/person/service.py`: identity-safe lookup and `PersonBootstrapService`;
  prevents reassignment by email, provisions missing records, and performs deletion cleanup.
- `src/pai/workflows/onboarding/service.py`: public onboarding status and next route.
- `src/pai/kernel/errors.py`: stable authentication/domain error codes and statuses.
- `src/pai/platform/database/db.py`: async database sessions, TLS, and pool behavior.
- `migrations/versions/`: schema history for identity links, counters, and related domain data.

### Diagnostics and tests

- `scripts/auth_diagnostics.py`: connectivity/timing diagnostics without secret output.
- `tests/test_auth_api.py`: endpoints, cookies, validation, verification, password and deletion flows.
- `tests/test_auth_hardening.py`: token integrity, recent auth, CSRF/origin, bounded profile loading,
  secure production settings, and provider edge cases.
- `tests/test_auth_limits.py`: Redis atomicity/outage policy, local limiter, shared budgets, and burst
  latency regression.
- `tests/test_jwt_verification.py`: signing algorithms, claims, cache, and rotation.
- `tests/test_supabase_provider.py`: provider request/response mapping and settings.
- `tests/conftest.py`: isolated fake provider, test settings, clients, and fixtures.

## 8. Configuration reference

```dotenv
APP_ENV=development
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
SUPABASE_JWT_AUDIENCE=authenticated

EMAIL_VERIFICATION_REDIRECT_URL=http://localhost:3000/auth/verify-email
PASSWORD_RESET_REDIRECT_URL=http://localhost:3000/auth/reset-password
CORS_ORIGINS=http://localhost:3000
TRUSTED_HOSTS=localhost,127.0.0.1

COOKIE_SECURE=false
COOKIE_SAME_SITE=lax
AUTH_HTTP_TIMEOUT_SECONDS=6.0
AUTH_PROFILE_TIMEOUT_SECONDS=1.0
AUTH_HTTP_MAX_CONNECTIONS=100
AUTH_HTTP_KEEPALIVE_CONNECTIONS=40
AUTH_RECENT_LOGIN_SECONDS=600
AUTH_ALLOW_LEGACY_HS256=true

ENABLE_RATE_LIMITS=true
AUTH_RATE_LIMIT_FAIL_CLOSED=true
RATE_LIMIT_REDIS_URL=
REDIS_TIMEOUT_SECONDS=0.5
AUTH_IP_LIMIT_PER_MINUTE=120
AUTH_LOGIN_LIMIT_PER_ACCOUNT=30
AUTH_EMAIL_LIMIT_PER_HOUR=5
AUTH_VERIFY_LIMIT_PER_ACCOUNT=10
```

Production changes at minimum:

```dotenv
APP_ENV=production
COOKIE_SECURE=true
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=api.example.com
EMAIL_VERIFICATION_REDIRECT_URL=https://app.example.com/auth/verify-email
PASSWORD_RESET_REDIRECT_URL=https://app.example.com/auth/reset-password
ENABLE_RATE_LIMITS=true
AUTH_RATE_LIMIT_FAIL_CLOSED=true
RATE_LIMIT_REDIS_URL=rediss://USER:PASSWORD@PRIVATE_REDIS:6379/0
AUTH_ALLOW_LEGACY_HS256=false
```

Use private networking and TLS for Redis. Keep API, Supabase, Redis, and database geographically
close. Never expose the service-role key to a browser or mobile bundle.

## 9. Frontend integration rules

1. Submit login once and disable the button while pending.
2. Keep the access token in memory where practical. Never persist the refresh token yourself.
3. Enable request credentials so the browser accepts and sends refresh cookies.
4. On one 401, perform one deduplicated refresh with the CSRF cookie/header, then retry once. If it
   fails, clear client authentication state and show login.
5. Use `nextPath` from login/verification instead of guessing onboarding state.
6. If `profilePending=true`, enter the authenticated UI and load `/me` in the background.
7. Respect `Retry-After` and never create automatic login retry loops.
8. On `REAUTHENTICATION_REQUIRED`, preserve the intended sensitive action, request sign-in, and
   resume only after a fresh authenticated token.
9. Treat logout as locally successful and clear frontend state.
10. Never log provider secrets, service-role keys, refresh tokens, or passwords.

## 10. Production checklist

- Supabase email confirmation and redirect allowlists match frontend URLs exactly.
- CAPTCHA remains disabled until the frontend and backend support it together.
- API and frontend use HTTPS; cookies are `Secure`.
- CORS and trusted hosts contain no wildcards.
- Shared private TLS Redis is configured and readiness reports it healthy.
- Rate limits are enabled and auth limits fail closed.
- Legacy HS256 is disabled when asymmetric signing keys are used.
- Database TLS verification and CA chain are valid.
- Migrations are at the expected head and readiness is healthy.
- Every API replica shares Redis; none uses local counters.
- CI auth tests and staging login/refresh/logout/recovery smoke tests pass.
- Metrics cover login latency, 401/403/429/503 rates, Redis, Supabase, JWKS, and deferred profile
  loads without recording sensitive data.

## 11. Verification commands

```powershell
uv run pytest tests/test_auth_api.py tests/test_auth_hardening.py tests/test_auth_limits.py `
  tests/test_jwt_verification.py tests/test_supabase_provider.py -q
uv run ruff check src/pai/interfaces/api/auth.py src/pai/interfaces/api/dependencies.py `
  src/pai/interfaces/api/schemas.py src/pai/platform/security/auth `
  src/pai/platform/limits.py src/pai/platform/redis_limits.py `
  src/pai/platform/request_limits.py
```

Restart the API after changing `.env`; settings and long-lived clients initialize once per process.
