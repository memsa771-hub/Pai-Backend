"""Strict user JWT verification with an asynchronous, per-project signing-key cache."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from jose import JOSEError, JWTError, jwk, jwt

from pai.config import Settings
from pai.kernel.errors import InvalidTokenError, ProviderUnavailableError


def _header(token: str, settings: Settings) -> dict:
    if not token or len(token) > 16384:
        raise InvalidTokenError("Invalid access token.")
    try:
        header = jwt.get_unverified_header(token)
    except (JWTError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Invalid access token.") from exc
    allowed = {"ES256", "RS256"}
    if settings.auth_allow_legacy_hs256:
        allowed.add("HS256")
    if header.get("alg") not in allowed:
        raise InvalidTokenError("Unsupported access token signing algorithm.")
    if header["alg"] != "HS256" and not isinstance(header.get("kid"), str):
        raise InvalidTokenError("Access token is missing its signing key ID.")
    return header


def validate_access_token(
    token: str, settings: Settings, keys: list[dict] | None = None
) -> dict[str, Any]:
    """CPU-only verification. Network callers must use JWTVerifier.verify()."""
    header = _header(token, settings)
    algorithm = header["alg"]
    key: Any = settings.supabase_jwt_secret
    if algorithm != "HS256":
        matching = [
            key
            for key in (keys or [])
            if key.get("kid") == header["kid"]
            and key.get("alg") == algorithm
            and key.get("use", "sig") == "sig"
        ]
        if len(matching) != 1:
            raise InvalidTokenError("Unknown access token signing key. Retry shortly.")
        try:
            key = jwk.construct(matching[0], algorithm=algorithm)
        except (JOSEError, ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid signing key.") from exc
    elif not key:
        raise InvalidTokenError("Legacy token signing is not configured.")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_auth_base,
            options={
                "require_exp": True,
                "require_iat": True,
                "require_sub": True,
                "require_aud": True,
                "require_iss": True,
                "leeway": 30,
            },
        )
        now = time.time()
        if (
            not payload["sub"]
            or payload.get("role") != "authenticated"
            or isinstance(payload["iat"], bool)
            or isinstance(payload["exp"], bool)
            or float(payload["iat"]) > now + 30
            or float(payload["exp"]) <= float(payload["iat"])
        ):
            raise InvalidTokenError("Invalid user access token.")
    except (JWTError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise InvalidTokenError(
            "Your session has expired or is invalid. Refresh and retry."
        ) from exc
    return payload


class JWTVerifier:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(3.0))
        self._lock = asyncio.Lock()
        self._keys: list[dict] = []
        self._fetched_at = float("-inf")
        self._attempted_at = float("-inf")

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _get_keys(self, kid: str) -> list[dict]:
        now = time.monotonic()
        known = any(key.get("kid") == kid for key in self._keys)
        if known and now - self._fetched_at < 600:
            return self._keys
        async with self._lock:
            now = time.monotonic()
            known = any(key.get("kid") == kid for key in self._keys)
            if known and now - self._fetched_at < 600:
                return self._keys
            # One refresh per project per cooldown, including unknown-key traffic.
            if now - self._attempted_at >= 30:
                self._attempted_at = now
                try:
                    response = await self.client.get(
                        f"{self.settings.supabase_auth_base}/.well-known/jwks.json",
                        headers={"apikey": self.settings.supabase_anon_key},
                    )
                    response.raise_for_status()
                    keys = response.json()["keys"]
                    if not isinstance(keys, list) or not all(isinstance(k, dict) for k in keys):
                        raise ValueError("Invalid JWKS response")
                    self._keys = keys
                    self._fetched_at = time.monotonic()
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    if not known or now - self._fetched_at >= 900:
                        raise ProviderUnavailableError(
                            "Session verification is temporarily unavailable."
                        ) from None
            if time.monotonic() - self._fetched_at >= 900:
                raise ProviderUnavailableError("Session verification is temporarily unavailable.")
            return self._keys

    async def verify(self, token: str) -> dict[str, Any]:
        header = _header(token, self.settings)
        keys = await self._get_keys(header["kid"]) if header["alg"] != "HS256" else None
        return validate_access_token(token, self.settings, keys)


def reset_jwks_cache_for_tests() -> None:
    """Compatibility: caches are now owned by each app, not process globals."""


def require_recent_auth(payload: dict, settings: Settings, *, methods=None) -> None:
    from pai.kernel.errors import AuthError

    allowed = methods or {"password", "otp", "totp", "oauth", "webauthn", "sso/saml"}
    now = time.time()
    for entry in payload.get("amr", []):
        if not isinstance(entry, dict) or entry.get("method") not in allowed:
            continue
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
            if -30 <= now - timestamp <= settings.auth_recent_login_seconds:
                return
    raise AuthError(
        "REAUTHENTICATION_REQUIRED", "Please sign in again to confirm this change.", 403
    )
