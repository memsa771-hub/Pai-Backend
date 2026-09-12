from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.domains.student.person.models import Person
from pai.domains.student.person.service import (
    PersonBootstrapService,
    soft_delete_person_data,
)
from pai.interfaces.api.dependencies import (
    get_db,
    get_pai,
    get_validated_access_token,
    limit_auth_attempt,
    require_csrf,
    require_recent_login,
)
from pai.interfaces.api.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    EmailOnlyRequest,
    LoginRequest,
    LoginResponseData,
    MeResponseData,
    MessageData,
    PasswordChangeRequest,
    PasswordResetRequest,
    SessionFromTokensRequest,
    SignupRequest,
    SignupResponseData,
    VerificationConfirmRequest,
    success,
)
from pai.kernel.errors import AuthError, PersonNotFoundError
from pai.platform.database.db import get_session_factory
from pai.platform.latency import span
from pai.platform.security.auth.provider import ProviderUser
from pai.platform.security.auth.service import AuthService, SessionBundle
from pai.workflows.onboarding.service import onboarding_public_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
account_router = APIRouter(prefix="/api/v1", tags=["account"])


def _set_session_cookies(response: Response, bundle: SessionBundle, settings: Settings) -> None:
    max_age = 60 * 60 * 24 * 30
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=bundle.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_same_site,
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=bundle.csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_same_site,
        max_age=max_age,
        path="/",
    )


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    for name in (settings.refresh_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name, path="/", secure=settings.cookie_secure, samesite=settings.cookie_same_site
        )


def _session_json(bundle: SessionBundle, onboarding: dict | None = None) -> dict:
    payload = {
        "accessToken": bundle.access_token,
        "accessTokenExpiresIn": bundle.access_token_expires_in,
        "user": {
            "id": bundle.user.id,
            "email": bundle.user.email,
            "emailVerified": bundle.user.email_verified,
            "displayName": bundle.user.display_name,
            "avatarUrl": bundle.user.avatar_url,
            "roles": bundle.user.roles or [],
            "createdAt": bundle.user.created_at,
        },
    }
    payload.update(
        onboarding or {"profilePending": True, "onboardingCompleted": None, "nextPath": None}
    )
    return success(payload)


def _session_response(
    bundle: SessionBundle, settings: Settings, onboarding: dict | None = None
) -> JSONResponse:
    response = JSONResponse(content=_session_json(bundle, onboarding))
    _set_session_cookies(response, bundle, settings)
    return response


async def _person_after_verified_auth(settings: Settings, user: ProviderUser) -> Person | None:
    """Attach Person after auth. Uses the token user (no extra Supabase /user call)."""
    if not user.email_verified:
        return None

    async def lookup():
        factory = get_session_factory(settings)
        async with factory() as session:
            # Existing logins need a read, not identity/vault writes and row locks.
            from sqlalchemy import select

            person = (
                await session.execute(
                    select(Person).where(
                        Person.external_auth_id == user.id,
                        Person.auth_provider == "supabase",
                    )
                )
            ).scalar_one_or_none()
            if person is not None:
                if person.deleted_at is not None or person.account_status != "active":
                    raise AuthError("ACCOUNT_UNAVAILABLE", "This account is not active.", 403)
                return person
            return await PersonBootstrapService(settings).ensure_person(session, user)

    try:
        from pai.platform.bounded_io import run_bounded

        return await run_bounded(
            lookup, settings.auth_profile_timeout_seconds, group="auth-profile"
        )
    except AuthError:
        raise
    except Exception as exc:
        logger.warning("Auth profile deferred (%s)", type(exc).__name__)
        return None


def _profile_status(person: Person | None, settings: Settings) -> dict:
    if person is None:
        return {"profilePending": True, "onboardingCompleted": None, "nextPath": None}
    return {"profilePending": False, **onboarding_public_status(person, settings)}


@router.post(
    "/signup",
    response_model=ApiSuccessResponse[SignupResponseData],
    responses={409: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
    summary="Register",
)
async def signup(
    request: Request,
    body: SignupRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    await limit_auth_attempt(request, settings, "signup", body.email)
    data = await service.signup(body.email, body.password, body.fullName)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=success(data))


@router.post(
    "/login",
    response_model=ApiSuccessResponse[LoginResponseData],
    responses={401: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
    summary="Login",
)
async def login(
    request: Request,
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    with span("auth_login_limit"):
        await limit_auth_attempt(request, settings, "login", body.email)
    with span("auth_provider_login"):
        bundle = await service.login(body.email, body.password)
    with span("auth_profile"):
        person = await _person_after_verified_auth(settings, bundle.user)
    return _session_response(bundle, settings, _profile_status(person, settings))


@router.post(
    "/refresh",
    response_model=ApiSuccessResponse[LoginResponseData],
    responses={401: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
    summary="Refresh token",
)
async def refresh_tokens(
    request: Request,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(require_csrf)],
) -> JSONResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        from pai.kernel.errors import InvalidTokenError

        raise InvalidTokenError("Refresh token cookie is missing.")
    bundle = await service.refresh(refresh_token)
    # Refresh is independent of profile availability. Keep its existing CSRF token
    # stable so concurrent tabs do not invalidate each other's in-flight requests.
    bundle.csrf_token = request.cookies[settings.csrf_cookie_name]
    return _session_response(bundle, settings)


@router.post(
    "/logout",
    response_model=ApiSuccessResponse[MessageData],
    responses={401: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
    summary="Logout",
)
async def logout(
    request: Request,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name, "")
    if refresh_token:
        await require_csrf(request, settings, request.headers.get("X-CSRF-Token"))
    authorization = request.headers.get("Authorization", "")
    access_token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    await service.logout(access_token, refresh_token)
    response = JSONResponse(content=success({"message": "Signed out successfully."}))
    _clear_session_cookies(response, settings)
    return response


@router.post(
    "/email-verification/request",
    response_model=ApiSuccessResponse[MessageData],
    summary="Resend verification email",
)
async def request_email_verification(
    request: Request,
    body: EmailOnlyRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    await limit_auth_attempt(request, settings, "resend", body.email)
    data = await service.resend_verification(body.email)
    return JSONResponse(content=success(data))


@router.post(
    "/email-verification/confirm",
    response_model=ApiSuccessResponse[LoginResponseData],
    responses={400: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
    summary="Confirm email",
)
async def confirm_email_verification(
    request: Request,
    body: VerificationConfirmRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    await limit_auth_attempt(request, settings, "verify", body.email)
    bundle = await service.confirm_verification(body.code, body.verifier, body.email)
    person = await _person_after_verified_auth(settings, bundle.user)
    return _session_response(bundle, settings, _profile_status(person, settings))


@router.post(
    "/session",
    response_model=ApiSuccessResponse[LoginResponseData],
    responses={401: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
    summary="Session from verify-email tokens",
)
async def establish_session(
    body: SessionFromTokensRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    bundle = await service.establish_session(body.accessToken, body.refreshToken)
    person = await _person_after_verified_auth(settings, bundle.user)
    return _session_response(bundle, settings, _profile_status(person, settings))


@router.post(
    "/password/forgot",
    response_model=ApiSuccessResponse[MessageData],
    summary="Forgot password",
)
async def forgot_password(
    request: Request,
    body: EmailOnlyRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    await limit_auth_attempt(request, settings, "forgot", body.email)
    data = await service.request_password_reset(body.email)
    return JSONResponse(content=success(data))


@router.post(
    "/password/reset",
    response_model=ApiSuccessResponse[MessageData],
    responses={400: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
    summary="Reset password",
)
async def reset_password(
    request: Request,
    body: PasswordResetRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    await limit_auth_attempt(request, settings, "recovery", body.email or body.ticket)
    data = await service.reset_password(
        body.ticket, body.newPassword, email=body.email, verifier=body.verifier
    )
    response = JSONResponse(content=success(data))
    _clear_session_cookies(response, settings)
    return response


@router.post(
    "/password/change",
    response_model=ApiSuccessResponse[MessageData],
    responses={
        401: {"model": ApiErrorResponse},
        403: {"model": ApiErrorResponse},
        501: {"model": ApiErrorResponse},
    },
    summary="Change password",
)
async def change_password(
    body: PasswordChangeRequest,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
    access_token: Annotated[str, Depends(require_recent_login)],
) -> JSONResponse:
    data = await service.change_password(access_token, body.newPassword)
    response = JSONResponse(content=success(data))
    _clear_session_cookies(response, settings)
    return response


@router.get(
    "/me",
    response_model=ApiSuccessResponse[MeResponseData],
    responses={401: {"model": ApiErrorResponse}},
    summary="Get current user",
)
async def me(
    request: Request,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
    access_token: Annotated[str, Depends(get_validated_access_token)],
) -> JSONResponse:
    user = await service.get_me(access_token)
    onboarding = _profile_status(None, settings)
    try:
        from pai.platform.database.db import get_session_factory

        factory = get_session_factory(settings)
        async with asyncio.timeout(5):
            async with factory() as session:
                person = await PersonBootstrapService(settings).ensure_person(session, user)
                onboarding = _profile_status(person, settings)
    except AuthError:
        raise
    except Exception as exc:
        logger.warning("Auth profile deferred (%s)", type(exc).__name__)
    return JSONResponse(
        content=success(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "emailVerified": user.email_verified,
                    "displayName": user.display_name,
                    "avatarUrl": user.avatar_url,
                    "roles": user.roles or [],
                    "createdAt": user.created_at,
                },
                **onboarding,
            }
        )
    )


@account_router.delete(
    "/account",
    response_model=ApiSuccessResponse[MessageData],
    responses={401: {"model": ApiErrorResponse}, 500: {"model": ApiErrorResponse}},
    summary="Delete account",
)
async def delete_account(
    request: Request,
    service: Annotated[AuthService, Depends(get_pai)],
    settings: Annotated[Settings, Depends(get_settings)],
    access_token: Annotated[str, Depends(require_recent_login)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    payload = request.state.auth_claims
    person = None
    try:
        from sqlalchemy import select

        from pai.domains.student.person.models import Person

        person = (
            await session.execute(
                select(Person).where(Person.external_auth_id == str(payload["sub"]))
            )
        ).scalar_one_or_none()
        if person is not None:
            await soft_delete_person_data(session, person)
    except PersonNotFoundError:
        pass
    except Exception as exc:
        await session.rollback()
        logger.exception("Application account cleanup failed; identity retained for retry")
        raise AuthError(
            "ACCOUNT_DELETE_INCOMPLETE",
            "Account cleanup is incomplete. Retry account deletion.",
            503,
        ) from exc
    try:
        await service.delete_account(access_token, refresh_token)
    except Exception as exc:
        logger.error(
            "Supabase account deletion failed after application data was anonymized "
            "(person_id=%s). Re-run provider deletion or restore from backup.",
            getattr(person, "id", None),
        )
        raise AuthError(
            code="ACCOUNT_DELETE_INCOMPLETE",
            message=(
                "Application profile was anonymized but identity deletion failed. "
                "Contact support to complete account removal."
            ),
            status_code=500,
        ) from exc
    response = JSONResponse(content=success({"message": "Account deleted successfully."}))
    _clear_session_cookies(response, settings)
    return response
