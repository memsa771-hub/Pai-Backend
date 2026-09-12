from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from pai.config import Settings
from pai.kernel.errors import (
    AuthError,
    EmailAlreadyInUseError,
    EmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    ProviderUnavailableError,
    UserNotFoundError,
    ValidationFailedError,
)
from pai.platform.security.auth.provider import (
    GenericActionResult,
    ProviderSession,
    ProviderUser,
    SignupResult,
)

logger = logging.getLogger(__name__)

SUPABASE_ERROR_MAP: dict[str, tuple[str, int]] = {
    "invalid_grant": ("INVALID_CREDENTIALS", 401),
    "invalid_credentials": ("INVALID_CREDENTIALS", 401),
    "email_not_confirmed": ("EMAIL_NOT_VERIFIED", 403),
    "user_not_found": ("USER_NOT_FOUND", 404),
    "user_already_exists": ("EMAIL_ALREADY_IN_USE", 409),
    "signup_disabled": ("FORBIDDEN", 403),
    "user_banned": ("FORBIDDEN", 403),
    "refresh_token_not_found": ("INVALID_TOKEN", 401),
    "invalid_refresh_token": ("INVALID_TOKEN", 401),
    "otp_expired": ("INVALID_TOKEN", 400),
    "over_email_send_rate_limit": ("VALIDATION_ERROR", 429),
    "over_request_rate_limit": ("PROVIDER_UNAVAILABLE", 503),
}


class SupabaseAuthProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = client is None
        timeout = httpx.Timeout(
            connect=3.0,
            read=settings.auth_http_timeout_seconds,
            write=settings.auth_http_timeout_seconds,
            pool=3.0,
        )
        limits = httpx.Limits(
            max_keepalive_connections=settings.auth_http_keepalive_connections,
            max_connections=settings.auth_http_max_connections,
            keepalive_expiry=30.0,
        )
        # Configure the transport itself: client limits do not override a supplied transport.
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0", limits=limits),
        )
        from pai.platform.security.auth.jwt import JWTVerifier

        self._verifier = JWTVerifier(settings, self._client)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def signup(self, email: str, password: str, full_name: str = "") -> SignupResult:
        redirect_to = self._settings.email_verification_redirect_url
        payload: dict[str, Any] = {
            "email": email,
            "password": password,
            "data": {
                "full_name": full_name,
                "display_name": full_name,
            },
            "options": {"email_redirect_to": redirect_to},
        }
        data = await self._request_json(
            "POST",
            "/signup",
            json_body=payload,
            params={"redirect_to": redirect_to},
        )
        identities = data.get("identities")
        if isinstance(identities, list) and identities == [] and data.get("id"):
            raise EmailAlreadyInUseError()
        if data.get("access_token") and data.get("user"):
            session = self._parse_token_response(data)
            if not session.user.email_verified:
                raise EmailNotVerifiedError()
            return SignupResult(session=session, message="Account created successfully.")
        return SignupResult(
            session=None,
            message="Account created. Please verify your email to continue.",
        )

    async def login(self, email: str, password: str) -> ProviderSession:
        payload: dict[str, Any] = {"email": email, "password": password}
        try:
            data = await self._request_json(
                "POST",
                "/token",
                params={"grant_type": "password"},
                json_body=payload,
            )
        except (InvalidCredentialsError, UserNotFoundError, IncorrectPasswordError):
            raise InvalidCredentialsError("Email or password is incorrect.") from None
        session = self._parse_token_response(data)
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return session

    async def refresh(self, refresh_token: str) -> ProviderSession:
        data = await self._request_json(
            "POST",
            "/token",
            params={"grant_type": "refresh_token"},
            json_body={"refresh_token": refresh_token},
        )
        return self._parse_token_response(data)

    async def logout(self, access_token: str, refresh_token: str) -> None:
        await self._request_json(
            "POST",
            "/logout",
            params={"scope": "local"},
            bearer_token=access_token,
            allow_empty_body=True,
        )

    async def resend_verification(self, email: str) -> GenericActionResult:
        payload = {
            "type": "signup",
            "email": email,
            "options": {"email_redirect_to": self._settings.email_verification_redirect_url},
        }
        await self._request_json("POST", "/resend", json_body=payload)
        return GenericActionResult(message=f"Verification email has been sent to {email}.")

    async def confirm_verification(
        self,
        code: str,
        verifier: str | None,
        email: str,
    ) -> ProviderSession:
        if verifier:
            data = await self._request_json(
                "POST",
                "/token",
                params={"grant_type": "pkce"},
                json_body={"auth_code": code, "code_verifier": verifier},
            )
        else:
            # Numeric OTPs use email+token; email-link hashes use token_hash.
            payload = (
                {"type": "signup", "token": code, "email": email}
                if code.isdigit()
                else {"type": "signup", "token_hash": code}
            )
            data = await self._request_json("POST", "/verify", json_body=payload)
        session = self._parse_token_response(data)
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return session

    async def request_password_reset(self, email: str) -> GenericActionResult:
        payload = {
            "email": email,
            "redirect_to": self._settings.password_reset_redirect_url,
        }
        await self._request_json(
            "POST",
            "/recover",
            json_body=payload,
            params={"redirect_to": self._settings.password_reset_redirect_url},
        )
        return GenericActionResult(
            message=f"A password recovery email has been sent to {email}.",
        )

    async def reset_password(
        self,
        ticket: str,
        new_password: str,
        *,
        email: str | None = None,
        verifier: str | None = None,
    ) -> GenericActionResult:
        if ticket.count(".") == 2:
            # Default implicit redirect already redeemed the recovery link.
            # /user checks this bearer with Supabase before any password mutation.
            access_token = ticket
            from pai.platform.security.auth.jwt import require_recent_auth

            claims = await self._verifier.verify(access_token)
            require_recent_auth(claims, self._settings, methods={"otp", "recovery"})
        else:
            if verifier:
                data = await self._request_json(
                    "POST",
                    "/token",
                    params={"grant_type": "pkce"},
                    json_body={"auth_code": ticket, "code_verifier": verifier},
                )
            else:
                payload = (
                    {"type": "recovery", "token": ticket, "email": email}
                    if email
                    else {"type": "recovery", "token_hash": ticket}
                )
                data = await self._request_json("POST", "/verify", json_body=payload)
            access_token = str(data.get("access_token", ""))
            if verifier and access_token:
                from pai.platform.security.auth.jwt import require_recent_auth

                claims = await self._verifier.verify(access_token)
                require_recent_auth(claims, self._settings, methods={"otp", "recovery"})
        if not access_token:
            raise InvalidTokenError()
        await self._request_json(
            "PUT",
            "/user",
            json_body={"password": new_password},
            bearer_token=access_token,
        )
        return GenericActionResult(message="Password has been reset successfully.")

    async def change_password(self, access_token: str, new_password: str) -> GenericActionResult:
        await self._request_json(
            "PUT",
            "/user",
            json_body={"password": new_password},
            bearer_token=access_token,
        )
        return GenericActionResult(
            message="Password changed successfully. Please sign in again.",
        )

    async def get_user(self, access_token: str) -> ProviderUser:
        data = await self._request_json("GET", "/user", bearer_token=access_token)
        return self._parse_user(data)

    async def delete_user(self, access_token: str) -> None:
        user = await self.get_user(access_token)
        await self._request_json(
            "DELETE",
            f"/admin/users/{user.id}",
            use_service_role=True,
            allow_empty_body=True,
        )

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(
                f"{self._settings.supabase_auth_base}/settings",
                headers=self._anon_headers(),
            )
            return response.status_code == 200
        except (httpx.TimeoutException, httpx.RequestError):
            return False

    def _anon_headers(self, bearer_token: str | None = None) -> dict[str, str]:
        key = self._settings.supabase_anon_key
        headers: dict[str, str] = {"apikey": key, "Content-Type": "application/json"}
        # New Supabase keys (sb_publishable_*) must not be sent as Bearer JWTs.
        if key.startswith("sb_publishable_") or key.startswith("sb_secret_"):
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
        else:
            headers["Authorization"] = f"Bearer {bearer_token or key}"
        return headers

    def _service_headers(self) -> dict[str, str]:
        key = self._settings.supabase_service_role_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if key.startswith("sb_secret_"):
            headers.pop("Authorization")
        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        bearer_token: str | None = None,
        use_service_role: bool = False,
        allow_empty_body: bool = False,
    ) -> dict[str, Any]:
        headers = self._service_headers() if use_service_role else self._anon_headers(bearer_token)
        url = f"{self._settings.supabase_auth_base}{path}"
        try:
            async with asyncio.timeout(self._settings.auth_http_timeout_seconds):
                response = await self._client.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    headers=headers,
                )
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise ProviderUnavailableError() from exc
        except httpx.RequestError as exc:
            logger.warning("Supabase auth request failed: %s", type(exc).__name__)
            raise ProviderUnavailableError() from exc

        if response.status_code >= 500:
            raise ProviderUnavailableError()

        if response.status_code == 429:
            exc = AuthError(
                "AUTH_RATE_LIMITED", "Too many attempts. Please try again shortly.", 429
            )
            try:
                exc.retry_after = max(1, min(3600, int(response.headers.get("Retry-After", "60"))))
            except ValueError:
                exc.retry_after = 60
            raise exc

        if response.status_code >= 400:
            self._raise_from_response(response)

        if allow_empty_body and not response.content:
            return {}

        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = response.json()
            except ValueError:
                raise ProviderUnavailableError() from None
            if isinstance(data, dict):
                return data
        raise ProviderUnavailableError("Authentication returned an unexpected response.")

    def _raise_from_response(self, response: httpx.Response) -> None:
        message = "Request could not be processed."
        code = "REQUEST_FAILED"
        status = response.status_code

        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                body = response.json()
            except ValueError:
                raise ProviderUnavailableError() from None
            if isinstance(body, dict):
                error_code = str(body.get("error") or body.get("error_code") or "")
                message = str(
                    body.get("msg")
                    or body.get("message")
                    or body.get("error_description")
                    or message
                )
                mapped = SUPABASE_ERROR_MAP.get(error_code)
                if mapped:
                    code, status = mapped
                elif error_code:
                    code = error_code.upper().replace(" ", "_")

        if "email not confirmed" in message.lower():
            code = "EMAIL_NOT_VERIFIED"
            status = 403
        if "invalid login credentials" in message.lower():
            code = "INVALID_CREDENTIALS"
            status = 401
        if "user not found" in message.lower():
            code = "USER_NOT_FOUND"
            status = 404

        if code == "INVALID_CREDENTIALS":
            raise InvalidCredentialsError(message)
        if code == "INCORRECT_PASSWORD":
            raise IncorrectPasswordError(message)
        if code == "USER_NOT_FOUND":
            raise UserNotFoundError(message)
        if code == "EMAIL_NOT_VERIFIED":
            raise EmailNotVerifiedError(message)
        if code == "EMAIL_ALREADY_IN_USE":
            raise EmailAlreadyInUseError(message)
        if code == "INVALID_TOKEN":
            raise InvalidTokenError(message)
        if code == "VALIDATION_ERROR":
            raise ValidationFailedError(message)
        if code == "PROVIDER_UNAVAILABLE":
            raise ProviderUnavailableError(message)
        raise AuthError(code=code, message=message, status_code=status)

    def _parse_user(self, data: dict[str, Any]) -> ProviderUser:
        metadata = data.get("user_metadata") or {}
        app_metadata = data.get("app_metadata") or {}
        roles = app_metadata.get("roles")
        if isinstance(roles, list):
            role_list = [str(r) for r in roles]
        else:
            role_list = ["authenticated"]

        return ProviderUser(
            id=str(data["id"]),
            email=data.get("email"),
            email_verified=data.get("email_confirmed_at") is not None,
            display_name=metadata.get("display_name") or metadata.get("full_name"),
            phone=metadata.get("phone") or data.get("phone"),
            avatar_url=metadata.get("avatar_url"),
            roles=role_list,
            created_at=data.get("created_at"),
        )

    def _parse_token_response(self, data: dict[str, Any]) -> ProviderSession:
        user_data = data.get("user")
        if not user_data:
            raise InvalidTokenError()
        user = self._parse_user(user_data)
        return ProviderSession(
            access_token=str(data["access_token"]),
            access_token_expires_in=int(data.get("expires_in", 3600)),
            refresh_token=str(data.get("refresh_token", "")),
            user=user,
        )
