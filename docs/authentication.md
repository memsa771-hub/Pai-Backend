# Authentication operations and client contract

The backend uses Supabase for credentials and refresh-token rotation. It verifies access JWTs
locally with strict issuer, audience, expiration, issued-at, subject, algorithm and user-role
checks. ES256/RS256 public keys are fetched asynchronously once per app and refreshed with a
30-second minimum interval. Cached keys are fresh for ten minutes; a provider outage permits
at most five additional minutes of stale-key use. There is no /user fallback for bad signatures.

## Login and refresh without unnecessary waiting

Login makes one Supabase password request. Existing profiles are read without row locks or
vault writes. Profile lookup/provisioning has a one-second default deadline and is cancelled
when it exceeds that deadline. An authenticated request or GET /api/v1/auth/me retries missing
profile provisioning; a failed lookup is never represented as completed or incomplete onboarding.
Slow cancellation/rollback cleanup runs off the response path; outstanding dependency tasks
are capped per event loop, so timeouts cannot create unbounded background work. First-time
profile initialization can also be completed explicitly with POST /api/v1/person/bootstrap
before retrying /me; do not repeatedly cancel a long first-time initialization from the client.

The successful login/session response now has `profilePending`. When true,
`onboardingCompleted` and `nextPath` are null. Store the access token in memory, show a brief
"Loading your profile" state, and call GET /api/v1/auth/me. If still pending, retry with bounded
backoff (for example 1, 2, 4 seconds); show a retry control after that. Do not log the user out or
send them to onboarding because profile loading failed. When false, use `nextPath` normally.

Refresh does not query the profile database. Its profile fields are pending/unknown: retain
the client's already-known onboarding state. Use one refresh promise per browser application,
coordinate tabs when possible (BroadcastChannel/Web Locks), and retry an API request at most
once after a 401. Never run an uncontrolled refresh/retry loop. 429 and 503 are not reasons to
erase a user's session. Respect Retry-After and use jitter. Preserve Supabase's refresh reuse
interval; do not independently replay or automatically retry token rotation on the server.

Use credentials: include for cookie requests and X-CSRF-Token from the readable CSRF cookie
for refresh/logout. The refresh cookie is HttpOnly. CSRF stays stable across refreshes so an
in-flight request from another tab is not invalidated. All auth responses are no-store. The
server rejects browser auth POSTs from origins outside CORS_ORIGINS. A same-origin reverse
proxy for /api is recommended: separate API subdomains cannot expose their host-only CSRF
cookie to frontend JavaScript. Native clients must manage their own cookie jar.

Logout supports an expired/missing access token when a refresh cookie is available. It
revokes the current Supabase session (scope=local), not all devices. A provider outage returns
503 without pretending revocation succeeded; preserve the cookie and offer retry. Existing
access JWTs can remain valid until expiration. This is not immediate revocation of every API
request. Configure the JWT lifetime consciously; use Supabase session controls for your policy.

## Recovery, verification and sensitive actions

Forgot password, resend, and signup return neutral messages for existing/nonexistent accounts.
Login returns INVALID_CREDENTIALS for either wrong email or wrong password.

POST /api/v1/auth/password/reset accepts newPassword, confirmPassword and ticket:

- For a custom recovery email link, ticket is `{{ .TokenHash }}`; send no email/verifier.
- For a numeric recovery OTP, send ticket plus email.
- For a PKCE redirect, send the authorization code as ticket plus the original verifier.
- For Supabase's default implicit redirect, send the access_token from the fragment as ticket.
  It must be a recently authenticated OTP/recovery JWT. Remove tokens from browser URL history
  immediately and never send them to analytics, logs, error trackers or referrer destinations.

The frontend must not redeem the same code/hash twice. For PKCE, the initiating Supabase
client must create and retain the verifier/challenge; this backend's signup endpoint does not
initiate a PKCE flow. Email confirmation accepts numeric OTPs, token hashes, or an existing
PKCE flow's code/verifier. /session accepts tokens from an already completed email redirect,
requires both to be valid, and rejects tokens belonging to different users.

Password change and account deletion require a verified bearer token, online user validation,
and a recent authentication event (default ten minutes). Refreshing an old session does not
count as signing in again. Handle REAUTHENTICATION_REQUIRED by asking the user to sign in and
then resume the intended action. Password reset through fresh email proof remains available.
The provider owns password hashing, password strength/breach controls and session invalidation
on password changes. Enable and test those provider settings. MFA enrollment/challenge UI is
not implemented in this repository; do not represent this release as a complete MFA product.

CAPTCHA is currently not part of the API contract. Login, signup, and forgot-password requests
do not accept or forward a captchaToken. Abuse protection currently relies on origin/CSRF checks
and distributed rate limits. If CAPTCHA is enabled later, add the frontend challenge and backend
verification together so users never see an unusable token field.

## Production deployment

The active environment file is **.env**, not `env`. Local credential files are excluded from
Git and deployment contexts. Never put credentials in example files.

Set at least:

```dotenv
APP_ENV=production
COOKIE_SECURE=true
COOKIE_SAME_SITE=lax
DATABASE_SSL_VERIFY=true
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=api.example.com
SUPABASE_URL=https://PROJECT.supabase.co
EMAIL_VERIFICATION_REDIRECT_URL=https://app.example.com/auth/verify-email
PASSWORD_RESET_REDIRECT_URL=https://app.example.com/auth/reset-password
RATE_LIMIT_REDIS_URL=rediss://USER:PASSWORD@YOUR-PRIVATE-REDIS:6379/0
AUTH_RATE_LIMIT_FAIL_CLOSED=true
ENABLE_RATE_LIMITS=true
ENABLE_API_DOCS=false
AUTH_HTTP_TIMEOUT_SECONDS=6
AUTH_PROFILE_TIMEOUT_SECONDS=1
REDIS_TIMEOUT_SECONDS=0.5
```

Production startup rejects insecure cookies, disabled database verification, wildcard hosts/
origins, HTTP auth URLs, missing shared Redis, and disabled auth limits. Legacy HS256 can be
disabled with AUTH_ALLOW_LEGACY_HS256=false after migrating Supabase signing keys. Do not copy
test signing keys into production. Database TLS retains the hostname for SNI/verification.
The Supabase Root 2021 public CA is bundled for Supabase database hosts (valid until 2031).
It comes from the certificate URL in Supabase's official dashboard source:
https://github.com/supabase/supabase/blob/master/apps/studio/hooks/custom-content/custom-content.json
For another private CA, set DATABASE_SSL_CA_FILE to a mounted PEM certificate file. Do not
disable verification to work around a missing trust root. Review CA rotation before expiry.

Use a dedicated shared Redis primary/Sentinel endpoint, with TLS/authentication, persistence,
replication/failover and noeviction. The multi-key Lua reservation is not Redis Cluster compatible.
Keep it close to the API; do not run independent regional counters if you require a global
account limit. Redis outages fail auth closed with bounded 503s; they do not shift traffic into
Postgres. Other usage-limit policies retain RATE_LIMIT_FAIL_CLOSED. Readiness includes Redis.

Local development automatically uses a process-local atomic limiter when
`RATE_LIMIT_REDIS_URL` is empty. It adds no network round trip and requires no manual service.
Local Redis is available with `docker compose up -d redis`; set
`RATE_LIMIT_REDIS_URL=redis://127.0.0.1:6379/0` to test the production-style backend.
The local limiter is intentionally per process and must never be used as a production substitute.
Do not disable rate limits in staging or production as a latency fix.

Defaults: 120 auth requests/IP/minute; 30 login attempts/account/5 minutes; 5 combined
signup/recovery/resend requests/account/hour; 10 verification attempts/account/5 minutes.
These are configurable and must be tuned from actual traffic. Account budgets can be abused
to cause temporary denial; pair them with edge bot protection and monitoring. They never
permanently lock an account. The middleware trusts the ASGI client address, not raw forwarded
headers: configure Uvicorn's trusted proxy IPs narrowly behind your load balancer.

Use custom SMTP, verified sender domains and delivery monitoring. Confirm production email
confirmation, redirect allowlists, JWT lifetime, refresh reuse, password protections and
security notification settings in Supabase. These remote settings were not changed here.

## Validation and capacity

Run focused checks with:

```powershell
python -m pytest tests/test_auth_api.py tests/test_supabase_provider.py tests/test_jwt_verification.py tests/test_auth_hardening.py tests/test_auth_limits.py -q
```

Tests use fake credentials, HTTP transports and a Lua-capable Redis emulator. They cover
rotation/outages, concurrent reservations, recovery contracts, CSRF, token-pair mismatches,
recent authentication and profile deadlines. The synthetic login burst is a concurrency
regression, not a production speed guarantee. No deployed database is truncated for these tests.

Measure p50/p95/p99 login and refresh time, errors, Redis timeouts, JWKS fetch failures, and
SMTP success in staging before rollout. Login timing logs separate auth_login_limit,
auth_provider_login and auth_profile without credentials. Existing request IDs correlate them.
Keep API, Redis and Supabase in nearby regions; profile lookups have a deadline but password
verification still depends on real network/provider latency. Load-test representative requests
per second and concurrent users rather than inferring capacity from registered-user count.
