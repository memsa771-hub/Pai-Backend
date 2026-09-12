"""Security and latency regressions; no deployed services or credentials are used."""

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jose import jwk, jwt
from pydantic import ValidationError

from pai.config import Settings
from pai.kernel.errors import AuthError, InvalidTokenError, ProviderUnavailableError
from pai.platform.security.auth.jwt import JWTVerifier, require_recent_auth, validate_access_token
from pai.platform.security.auth.provider import ProviderSession, ProviderUser
from pai.platform.security.auth.service import AuthService
from pai.platform.security.auth.supabase import SupabaseAuthProvider


def claims(settings, **overrides):
    now = int(time.time())
    return {
        "sub": "user-1",
        "iss": settings.supabase_auth_base,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "amr": [{"method": "password", "timestamp": now}],
        **overrides,
    }


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub", "role"])
def test_required_claims(test_settings, missing):
    payload = claims(test_settings)
    payload.pop(missing)
    token = jwt.encode(payload, test_settings.supabase_jwt_secret, algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        validate_access_token(token, test_settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://other.supabase.co/auth/v1"},
        {"aud": "other"},
        {"role": "service_role"},
        {"role": "anon"},
        {"sub": ""},
        {"exp": 1},
        {"iat": 9999999999},
    ],
)
def test_invalid_claims(test_settings, overrides):
    token = jwt.encode(
        claims(test_settings, **overrides), test_settings.supabase_jwt_secret, algorithm="HS256"
    )
    with pytest.raises(InvalidTokenError):
        validate_access_token(token, test_settings)


def test_invalid_signature_and_disabled_legacy(test_settings):
    token = jwt.encode(claims(test_settings), "wrong-signing-key", algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        validate_access_token(token, test_settings)
    token = jwt.encode(claims(test_settings), test_settings.supabase_jwt_secret, algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        validate_access_token(
            token, test_settings.model_copy(update={"auth_allow_legacy_hs256": False})
        )


def signed_asymmetric(settings, alg="ES256", kid="key-1"):
    private = (
        ec.generate_private_key(ec.SECP256R1())
        if alg == "ES256"
        else rsa.generate_private_key(65537, 2048)
    )
    pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public = jwk.construct(pem, algorithm=alg).public_key().to_dict()
    public.update(kid=kid, alg=alg, use="sig")
    token = jwt.encode(claims(settings), pem, algorithm=alg, headers={"kid": kid})
    return token, public


@pytest.mark.parametrize("alg", ["ES256", "RS256"])
async def test_asymmetric_verification_is_concurrent_and_single_fetch(test_settings, alg):
    token, public = signed_asymmetric(test_settings, alg)
    requests = []
    ticked = asyncio.Event()

    async def handler(request):
        requests.append(request)
        await asyncio.sleep(0.03)
        assert ticked.is_set(), "Key fetching blocked the event loop"
        return httpx.Response(200, json={"keys": [public]})

    async def ticker():
        await asyncio.sleep(0.005)
        ticked.set()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = JWTVerifier(test_settings, client)
        results = await asyncio.gather(ticker(), *(verifier.verify(token) for _ in range(30)))
        assert all(result["sub"] == "user-1" for result in results[1:])
        assert len(requests) == 1
        await verifier.verify(token)
        assert len(requests) == 1


async def test_unknown_key_cooldown_rotation_and_bounded_stale_cache(test_settings):
    token, public = signed_asymmetric(test_settings)
    new_token, new_public = signed_asymmetric(test_settings, kid="key-2")
    responses = [{"keys": [public]}, {"keys": [new_public]}]
    count = 0

    async def handler(request):
        nonlocal count
        count += 1
        if responses:
            return httpx.Response(200, json=responses.pop(0))
        raise httpx.ConnectError("offline")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = JWTVerifier(test_settings, client)
        await verifier.verify(token)
        for _ in range(20):
            with pytest.raises(InvalidTokenError):
                await verifier.verify(new_token)
        assert count == 1
        verifier._attempted_at -= 31
        await verifier.verify(new_token)
        assert count == 2
        with pytest.raises(InvalidTokenError):
            await verifier.verify(token)
        verifier._fetched_at -= 601
        verifier._attempted_at -= 31
        await verifier.verify(new_token)  # Brief, bounded outage tolerance.
        verifier._fetched_at -= 301
        with pytest.raises(ProviderUnavailableError):
            await verifier.verify(new_token)


async def test_session_rejects_mixed_users_and_invalid_refresh():
    a = ProviderUser("a", "a@example.com", True)
    b = ProviderUser("b", "b@example.com", True)
    provider = SimpleNamespace(
        get_user=AsyncMock(return_value=a),
        refresh=AsyncMock(return_value=ProviderSession("access-b", 3600, "refresh-b", b)),
    )
    service = AuthService(provider)
    with pytest.raises(InvalidTokenError):
        await service.establish_session("access-a", "refresh-b")
    provider.refresh.side_effect = InvalidTokenError()
    with pytest.raises(InvalidTokenError):
        await service.establish_session("access-a", "invalid")


async def test_logout_recovers_expired_access_and_revokes_current_session():
    session = ProviderSession("new-access", 3600, "new-refresh", ProviderUser("a", None, True))
    provider = SimpleNamespace(
        logout=AsyncMock(side_effect=[InvalidTokenError(), None]),
        refresh=AsyncMock(return_value=session),
    )
    await AuthService(provider).logout("expired", "refresh")
    provider.refresh.assert_awaited_once_with("refresh")
    assert provider.logout.await_args_list[-1].args == ("new-access", "new-refresh")


@pytest.mark.parametrize("email", [None, "user@example.com"])
async def test_recovery_contract(test_settings, email):
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        if request.url.path.endswith("/verify"):
            expected = (
                {"type": "recovery", "token": "123456", "email": email}
                if email
                else {"type": "recovery", "token_hash": "hash-value"}
            )
            assert body == expected
            return httpx.Response(200, json={"access_token": "recovery-access"})
        assert request.method == "PUT" and request.url.path.endswith("/user")
        assert body == {"password": "new-password"}
        assert request.headers["authorization"] == "Bearer recovery-access"
        return httpx.Response(200, json={"id": "user-1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SupabaseAuthProvider(test_settings, client)
        await provider.reset_password(
            "123456" if email else "hash-value", "new-password", email=email
        )
    assert len(requests) == 2


async def test_password_login_token_cannot_be_used_as_recovery_ticket(test_settings):
    def handler(request):
        pytest.fail("No password mutation should be attempted")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SupabaseAuthProvider(test_settings, client)
        token = jwt.encode(
            claims(test_settings), test_settings.supabase_jwt_secret, algorithm="HS256"
        )
        with pytest.raises(AuthError, match="sign in again"):
            await provider.reset_password(token, "new-password")


def test_refresh_iat_does_not_satisfy_recent_auth(test_settings):
    payload = claims(test_settings, amr=[{"method": "password", "timestamp": time.time() - 3600}])
    with pytest.raises(AuthError):
        require_recent_auth(payload, test_settings)
    require_recent_auth(claims(test_settings), test_settings)


async def test_rate_limit_preserves_429_and_retry_after(test_settings):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "42"}, json={})
        )
    ) as client:
        with pytest.raises(AuthError) as error:
            await SupabaseAuthProvider(test_settings, client).login("a@example.com", "wrong")
    assert error.value.status_code == 429
    assert error.value.retry_after == 42


async def test_slow_profile_has_deadline_and_is_cancelled(test_settings, monkeypatch):
    from pai.interfaces.api.auth import _person_after_verified_auth

    cancelled = asyncio.Event()

    class SlowSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, *args):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()

    monkeypatch.setattr("pai.interfaces.api.auth.get_session_factory", lambda settings: SlowSession)
    settings = test_settings.model_copy(update={"auth_profile_timeout_seconds": 0.04})
    start = time.perf_counter()
    person = await _person_after_verified_auth(settings, ProviderUser("a", "a@example.com", True))
    await asyncio.sleep(0)
    assert person is None and cancelled.is_set()
    assert time.perf_counter() - start < 0.5


def test_production_rejects_insecure_settings(test_settings):
    values = test_settings.model_dump()
    values.update(app_env="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
    values.update(
        cookie_secure=True,
        database_ssl_verify=True,
        cors_origins=["https://app.example.com"],
        trusted_hosts=["api.example.com"],
        email_verification_redirect_url="https://app.example.com/auth/verify",
        password_reset_redirect_url="https://app.example.com/auth/reset",
        rate_limit_redis_url="redis://127.0.0.1:6379/0",
        auth_allow_legacy_hs256=False,
    )
    assert Settings(_env_file=None, **values).app_env == "production"


def test_database_tls_preserves_hostname():
    from pai.platform.database.db import _engine_connect_args

    args = _engine_connect_args("postgresql+asyncpg://u:p@db.example.supabase.co/db")
    assert args["ssl"].check_hostname is True
    assert "host" not in args


def test_auth_responses_not_cached_and_cross_origin_login_rejected(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong"}
    )
    assert response.headers["cache-control"] == "no-store"
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example"},
        json={"email": "a@example.com", "password": "wrong"},
    )
    assert response.status_code == 403


def test_same_origin_swagger_login_is_allowed(client):
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://testserver"},
        json={"email": "a@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_sensitive_action_requires_recent_login(client, fake_provider, test_settings):
    payload = claims(test_settings, amr=[{"method": "password", "timestamp": time.time() - 3600}])
    token = jwt.encode(payload, test_settings.supabase_jwt_secret, algorithm="HS256")
    response = client.post(
        "/api/v1/auth/password/change",
        headers={"Authorization": f"Bearer {token}"},
        json={"newPassword": "new-password", "confirmPassword": "new-password"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REAUTHENTICATION_REQUIRED"
    assert fake_provider.get_user_calls == 0


async def test_deadline_does_not_wait_for_driver_rollback_and_caps_pending_work():
    from pai.platform.bounded_io import run_bounded

    cleanup_started = asyncio.Event()
    release = asyncio.Event()

    async def operation():
        try:
            await asyncio.sleep(10)
        finally:
            cleanup_started.set()
            await release.wait()

    start = time.perf_counter()
    with pytest.raises(TimeoutError):
        await run_bounded(operation, 0.02, group="test-slow-cleanup", max_pending=1)
    assert time.perf_counter() - start < 0.2
    await cleanup_started.wait()
    with pytest.raises(TimeoutError, match="concurrency budget"):
        await run_bounded(operation, 1, group="test-slow-cleanup", max_pending=1)
    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)


async def test_verification_pkce_is_actually_exchanged(test_settings):
    def handler(request):
        assert request.url.params["grant_type"] == "pkce"
        assert json.loads(request.content) == {"auth_code": "code", "code_verifier": "v" * 43}
        return httpx.Response(
            200,
            json={
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "user": {"id": "a", "email_confirmed_at": "2026-01-01"},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        session = await SupabaseAuthProvider(test_settings, client).confirm_verification(
            "code", "v" * 43, "a@example.com"
        )
    assert session.user.id == "a"


async def test_malformed_provider_response_is_retryable(test_settings):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, text="not-json", headers={"content-type": "application/json"}
            )
        )
    ) as client:
        with pytest.raises(ProviderUnavailableError):
            await SupabaseAuthProvider(test_settings, client).login("a@example.com", "wrong")


async def test_existing_email_does_not_reassign_student_identity(test_settings, monkeypatch):
    from contextlib import asynccontextmanager

    from pai.domains.student.person.service import PersonBootstrapService

    @asynccontextmanager
    async def transaction():
        yield

    existing = SimpleNamespace(external_auth_id="original-owner")
    service = PersonBootstrapService(test_settings)
    monkeypatch.setattr(service, "_get_person_for_update", AsyncMock(return_value=None))
    monkeypatch.setattr(
        service, "_get_live_person_by_email_for_update", AsyncMock(return_value=existing)
    )
    with pytest.raises(AuthError) as result:
        await service.bootstrap(
            SimpleNamespace(begin=transaction),
            ProviderUser("different-owner", "same@example.com", True),
        )
    assert result.value.code == "IDENTITY_LINK_REQUIRED"
    assert existing.external_auth_id == "original-owner"


async def test_suspended_profile_cannot_access_protected_data():
    from pai.domains.student.person.service import get_person_by_auth

    person = SimpleNamespace(account_status="suspended")
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: person))
    )
    with pytest.raises(AuthError) as result:
        await get_person_by_auth(session, "user-1")
    assert result.value.code == "ACCOUNT_UNAVAILABLE"


async def test_existing_login_profile_is_read_only(test_settings, monkeypatch):
    from pai.domains.student.person.service import PersonBootstrapService
    from pai.interfaces.api.auth import _person_after_verified_auth

    person = SimpleNamespace(account_status="active", deleted_at=None)

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, statement):
            return SimpleNamespace(scalar_one_or_none=lambda: person)

    ensure = AsyncMock(side_effect=AssertionError("Existing login must not write the profile"))
    monkeypatch.setattr(PersonBootstrapService, "ensure_person", ensure)
    monkeypatch.setattr("pai.interfaces.api.auth.get_session_factory", lambda settings: Session)
    assert await _person_after_verified_auth(test_settings, ProviderUser("a", None, True)) is person
    ensure.assert_not_called()
