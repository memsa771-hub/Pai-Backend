from __future__ import annotations

import secrets
from dataclasses import dataclass

from pai.kernel.errors import (
    AuthError,
    EmailAlreadyInUseError,
    EmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from pai.platform.security.auth.provider import AuthProvider, ProviderSession, ProviderUser


@dataclass(slots=True)
class SessionBundle:
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    csrf_token: str
    user: ProviderUser


class AuthService:
    def __init__(self, provider: AuthProvider) -> None:
        self._provider = provider

    @staticmethod
    def new_csrf_token() -> str:
        return secrets.token_urlsafe(32)

    async def signup(self, email: str, password: str, full_name: str = "") -> dict:
        normalized = email.strip().lower()
        try:
            await self._provider.signup(normalized, password, full_name)
        except EmailAlreadyInUseError:
            pass
        return {
            "message": (
                "If registration is available for this email, a verification link has been sent. "
                "If you already have an account, sign in or reset your password."
            ),
            "email": normalized,
        }

    async def login(self, email: str, password: str) -> SessionBundle:
        try:
            session = await self._provider.login(email.strip().lower(), password)
        except (UserNotFoundError, IncorrectPasswordError, InvalidCredentialsError):
            raise InvalidCredentialsError() from None
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return self._to_bundle(session)

    async def refresh(self, refresh_token: str) -> SessionBundle:
        session = await self._provider.refresh(refresh_token)
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return self._to_bundle(session)

    async def logout(self, access_token: str, refresh_token: str) -> None:
        if access_token:
            try:
                await self._provider.logout(access_token, refresh_token)
                return
            except AuthError as exc:
                if exc.status_code not in {401, 403}:
                    raise
        if refresh_token:
            try:
                session = await self._provider.refresh(refresh_token)
                await self._provider.logout(session.access_token, session.refresh_token)
            except AuthError as exc:
                if exc.status_code not in {401, 403}:
                    raise

    async def resend_verification(self, email: str) -> dict:
        normalized = email.strip().lower()
        try:
            await self._provider.resend_verification(normalized)
        except UserNotFoundError:
            pass
        return {"message": "If this account needs verification, an email has been sent."}

    async def confirm_verification(
        self, code: str, verifier: str | None, email: str
    ) -> SessionBundle:
        session = await self._provider.confirm_verification(code, verifier, email)
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return self._to_bundle(session)

    async def establish_session(self, access_token: str, refresh_token: str) -> SessionBundle:
        """Turn tokens from the email-verification redirect into a PAI session."""
        user = await self._provider.get_user(access_token)
        if not user.email_verified:
            raise EmailNotVerifiedError()
        session = await self._provider.refresh(refresh_token)
        if session.user.id != user.id:
            raise InvalidTokenError("Session tokens do not belong to the same account.")
        if not session.user.email_verified:
            raise EmailNotVerifiedError()
        return self._to_bundle(session)

    async def request_password_reset(self, email: str) -> dict:
        normalized = email.strip().lower()
        try:
            await self._provider.request_password_reset(normalized)
        except UserNotFoundError:
            pass
        return {"message": "If an account exists for this email, a recovery link has been sent."}

    async def reset_password(
        self, ticket: str, new_password: str, *, email=None, verifier=None
    ) -> dict:
        options = {
            key: value for key, value in {"email": email, "verifier": verifier}.items() if value
        }
        result = await self._provider.reset_password(ticket, new_password, **options)
        return {"message": result.message}

    async def change_password(self, access_token: str, new_password: str) -> dict:
        result = await self._provider.change_password(access_token, new_password)
        return {"message": result.message}

    async def get_me(self, access_token: str) -> ProviderUser:
        return await self._provider.get_user(access_token)

    async def delete_account(self, access_token: str, refresh_token: str | None) -> None:
        await self._provider.delete_user(access_token)
        if refresh_token:
            try:
                await self._provider.logout(access_token, refresh_token)
            except AuthError:
                pass

    def _to_bundle(self, session: ProviderSession) -> SessionBundle:
        return SessionBundle(
            access_token=session.access_token,
            access_token_expires_in=session.access_token_expires_in,
            refresh_token=session.refresh_token,
            csrf_token=self.new_csrf_token(),
            user=session.user,
        )

    @staticmethod
    def _public_session(session: ProviderSession, *, include_refresh: bool) -> dict:
        data = {
            "accessToken": session.access_token,
            "accessTokenExpiresIn": session.access_token_expires_in,
            "user": AuthService._public_user(session.user),
        }
        if include_refresh:
            data["refreshToken"] = session.refresh_token
        return data

    @staticmethod
    def _public_user(user: ProviderUser) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "emailVerified": user.email_verified,
            "displayName": user.display_name,
            "avatarUrl": user.avatar_url,
            "roles": user.roles or [],
            "createdAt": user.created_at,
        }
