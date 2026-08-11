import httpx
import pytest

from auth_service.config import Settings
from auth_service.core.errors import InvalidCredentialsError, ProviderUnavailableError
from auth_service.providers.supabase import SupabaseAuthProvider


@pytest.fixture
def supabase_settings() -> Settings:
    return Settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
        SUPABASE_SERVICE_ROLE_KEY="service-key",
        SUPABASE_JWT_SECRET="jwt-secret",
        EMAIL_VERIFICATION_REDIRECT_URL="http://localhost:3000/verify",
        PASSWORD_RESET_REDIRECT_URL="http://localhost:3000/reset",
        CORS_ORIGINS="http://localhost:3000",
        TRUSTED_HOSTS="testserver",
        DATABASE_URL="postgresql+asyncpg://pai:pai@127.0.0.1:5433/pai_auth",
        VAULT_ENCRYPTION_KEY="nAiPKgHP0wblQhCFnmH_2hRsQts1BmOKdHQUa2m0FzQ=",
    )


@pytest.mark.asyncio
async def test_supabase_login_maps_invalid_credentials(supabase_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "Invalid login credentials",
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = SupabaseAuthProvider(supabase_settings, client=client)

    with pytest.raises(InvalidCredentialsError):
        await provider.login("a@example.com", "wrong")

    await provider.aclose()


@pytest.mark.asyncio
async def test_supabase_timeout_raises_provider_unavailable(supabase_settings: Settings):
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = SupabaseAuthProvider(supabase_settings, client=client)

    with pytest.raises(ProviderUnavailableError):
        await provider.login("a@example.com", "Password123!")

    await provider.aclose()


@pytest.mark.asyncio
async def test_supabase_signup_without_session(supabase_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/signup")
        return httpx.Response(
            200,
            json={
                "id": "user-id",
                "email": "new@example.com",
                "email_confirmed_at": None,
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = SupabaseAuthProvider(supabase_settings, client=client)

    result = await provider.signup("new@example.com", "Password123!")
    assert result.session is None

    await provider.aclose()
