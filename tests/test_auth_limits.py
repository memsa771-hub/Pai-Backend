import asyncio
import time
from unittest.mock import AsyncMock

import fakeredis
import fakeredis.aioredis
import httpx
import pytest

from pai.kernel.errors import AuthError
from pai.platform import redis_limits
from pai.platform.limits import LimitExceeded, _local_buckets, consume


@pytest.fixture
async def redis_client(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_limits, "get_client", lambda settings: client)
    yield client
    await client.aclose()


def limited_settings(test_settings):
    return test_settings.model_copy(
        update={
            "app_env": "development",
            "rate_limit_redis_url": "redis://local-test",
            "redis_timeout_seconds": 2,
        }
    )


async def test_development_without_redis_uses_fast_local_limits(test_settings):
    _local_buckets.clear()
    settings = test_settings.model_copy(
        update={
            "app_env": "development",
            "enable_rate_limits": True,
            "rate_limit_redis_url": "",
        }
    )
    await consume(settings, [("auth_login", "a@example.com", 1, 2, 300)], fail_closed=True)
    await consume(settings, [("auth_login", "a@example.com", 1, 2, 300)], fail_closed=True)
    with pytest.raises(LimitExceeded):
        await consume(
            settings,
            [("auth_login", "a@example.com", 1, 2, 300)],
            fail_closed=True,
        )
    _local_buckets.clear()


async def test_concurrent_reservations_cannot_overspend(test_settings, redis_client):
    settings = limited_settings(test_settings)

    async def request():
        try:
            await consume(settings, [("login", "a@example.com", 1, 10, 300)], fail_closed=True)
            return True
        except LimitExceeded:
            return False

    results = await asyncio.gather(*(request() for _ in range(50)))
    assert sum(results) == 10
    keys = await redis_client.keys("*")
    assert len(keys) == 1 and "a@example.com" not in keys[0]
    assert 0 < await redis_client.ttl(keys[0]) <= 301


async def test_multi_counter_rejection_does_not_partially_charge(test_settings, redis_client):
    settings = limited_settings(test_settings)
    await consume(settings, [("global", "all", 1, 1, 300)], fail_closed=True)
    with pytest.raises(LimitExceeded):
        await consume(
            settings, [("person", "a", 1, 100, 300), ("global", "all", 1, 1, 300)], fail_closed=True
        )
    assert not await redis_client.keys("pai:limits:person:*")


async def test_new_window_resets_counter(test_settings, redis_client):
    settings = limited_settings(test_settings)
    await consume(settings, [("login", "a", 1, 1, 300)], fail_closed=True)
    key = (await redis_client.keys("*"))[0]
    await redis_client.hset(key, "bucket", 0)
    await consume(settings, [("login", "a", 1, 1, 300)], fail_closed=True)
    assert await redis_client.hget(key, "used") == "1"


async def test_auth_fails_closed_without_postgres_fallback(test_settings, monkeypatch):
    settings = limited_settings(test_settings)
    monkeypatch.setattr(redis_limits, "reserve", AsyncMock(side_effect=ConnectionError("offline")))

    def forbidden(settings):
        pytest.fail("Redis outage must not move attack traffic to PostgreSQL")

    monkeypatch.setattr("pai.platform.limits.get_session_factory", forbidden)
    with pytest.raises(AuthError) as result:
        await consume(settings, [("auth_login", "a", 1, 30, 300)], fail_closed=True)
    assert result.value.code == "LIMITS_UNAVAILABLE"


async def test_auth_limit_timeout_is_bounded(test_settings, monkeypatch):
    settings = limited_settings(test_settings).model_copy(update={"redis_timeout_seconds": 0.03})

    async def slow(*args):
        await asyncio.sleep(5)

    monkeypatch.setattr(redis_limits, "reserve", slow)
    started = time.perf_counter()
    with pytest.raises(AuthError):
        await consume(settings, [("auth_login", "a", 1, 30, 300)], fail_closed=True)
    assert time.perf_counter() - started < 0.5


async def test_shared_email_budget_across_endpoints_and_replicas(test_settings, redis_client):
    from pai.interfaces.api.dependencies import limit_auth_attempt

    settings = limited_settings(test_settings).model_copy(update={"auth_email_limit_per_hour": 2})
    await limit_auth_attempt(None, settings, "signup", "A@example.com")
    await limit_auth_attempt(None, settings, "forgot", "a@example.com")
    with pytest.raises(LimitExceeded):
        await limit_auth_attempt(None, settings, "resend", "a@example.com")


async def test_login_burst_has_no_database_rate_limit_work(
    test_settings, redis_client, monkeypatch
):
    """Synthetic concurrency regression, not a measurement of Supabase/network latency."""
    from fastapi import FastAPI

    from pai.config import get_settings
    from pai.interfaces.api.auth import router
    from pai.interfaces.api.dependencies import get_auth_provider
    from pai.platform.request_limits import RequestLimitsMiddleware
    from pai.platform.security.auth.provider import ProviderSession, ProviderUser

    settings = limited_settings(test_settings).model_copy(
        update={"auth_profile_timeout_seconds": 0.05, "auth_ip_limit_per_minute": 1000}
    )

    class Provider:
        async def login(self, email, password):
            await asyncio.sleep(0.02)
            return ProviderSession("access", 3600, "refresh", ProviderUser(email, email, True))

    class SlowSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, *args):
            await asyncio.sleep(10)

    monkeypatch.setattr("pai.interfaces.api.auth.get_session_factory", lambda settings: SlowSession)
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_provider] = lambda: Provider()
    app.include_router(router)
    app.add_middleware(RequestLimitsMiddleware, settings=settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://testserver"
    ) as client:
        started = time.perf_counter()
        responses = await asyncio.gather(
            *(
                client.post(
                    "/api/v1/auth/login",
                    json={"email": f"user{i}@example.com", "password": "password"},
                )
                for i in range(50)
            )
        )
        elapsed = time.perf_counter() - started
    assert all(r.status_code == 200 and r.json()["data"]["profilePending"] for r in responses)
    assert elapsed < 2, f"50 concurrent logins serialized: {elapsed:.3f}s"
    print(f"Synthetic 50-login burst: {elapsed:.3f}s; 20ms provider delay, 50ms profile deadline")
