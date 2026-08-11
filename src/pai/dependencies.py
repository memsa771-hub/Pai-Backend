from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.core.errors import CsrfError, InvalidTokenError
from pai.core.provider import AuthProvider
from pai.core.service import AuthService
from pai.data.db import get_session_factory
from pai.openapi import BEARER_DESCRIPTION
from pai.person.models import Person
from pai.person.service import get_person_by_auth
from pai.security.jwt import validate_access_token

_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=BEARER_DESCRIPTION,
)

__all__ = [
    "get_auth_provider",
    "get_pai",
    "get_current_access_token",
    "get_validated_access_token",
    "get_db",
    "resolve_person_from_token",
    "require_csrf",
    "validate_access_token",
]


def get_auth_provider(request: Request) -> AuthProvider:
    return request.app.state.auth_provider


def get_pai(
    provider: Annotated[AuthProvider, Depends(get_auth_provider)],
) -> AuthService:
    return AuthService(provider)


async def get_current_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if credentials is None:
        raise InvalidTokenError(
            "Missing Authorization header. In Swagger: Authorize with data.accessToken "
            "from login (paste token only, no 'Bearer' prefix)."
        )
    if credentials.scheme.lower() != "bearer":
        raise InvalidTokenError(
            "Authorization scheme must be Bearer. Paste only the JWT in Swagger Authorize."
        )
    token = (credentials.credentials or "").strip()
    if not token or token.lower().startswith("bearer "):
        raise InvalidTokenError(
            "Invalid access token. Paste only the eyJ… JWT — do not include the word Bearer."
        )
    return token


async def get_validated_access_token(
    token: Annotated[str, Depends(get_current_access_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    validate_access_token(token, settings)
    return token


def _constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())


async def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AsyncSession]:
    factory = get_session_factory(settings)
    async with factory() as session:
        yield session


async def resolve_person_from_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_validated_access_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Person:
    payload = validate_access_token(token, settings)
    external_id = str(payload["sub"])
    return await get_person_by_auth(session, external_id)


async def require_csrf(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if not cookie_token or not csrf_header or not _constant_time_equals(cookie_token, csrf_header):
        raise CsrfError()
