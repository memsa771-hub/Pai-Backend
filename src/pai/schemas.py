from __future__ import annotations

import re
from typing import Any, Self, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

T = TypeVar("T")


class ApiErrorBody(BaseModel):
    code: str = Field(examples=["INVALID_CREDENTIALS"])
    message: str = Field(examples=["Email or password is incorrect."])


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorBody


class ApiSuccessResponse[T](BaseModel):
    success: bool = True
    data: T


def _passwords_must_match(password: str, confirm: str) -> None:
    if password != confirm:
        raise ValueError("Passwords do not match.")


def _normalize_phone(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value.strip())
    if not re.fullmatch(r"\+?[0-9]{8,15}", compact):
        raise ValueError("Enter a valid phone number.")
    return compact


class SignupRequest(BaseModel):
    fullName: str = Field(min_length=2, max_length=256, examples=["Ali Khan"])
    email: EmailStr = Field(examples=["user@example.com"])
    phone: str = Field(min_length=8, max_length=32, examples=["+923001234567"])
    password: str = Field(min_length=8, max_length=128, examples=["Str0ngPass#1"])
    confirmPassword: str = Field(min_length=8, max_length=128, examples=["Str0ngPass#1"])

    @field_validator("fullName", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return _normalize_phone(value)

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        _passwords_must_match(self.password, self.confirmPassword)
        return self


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(min_length=1, max_length=128, examples=["Str0ngPass#1"])


class EmailOnlyRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])


class VerificationConfirmRequest(BaseModel):
    code: str = Field(min_length=1, description="Verification token from the email link (`token=` query param).")
    email: EmailStr = Field(examples=["user@example.com"], description="Same email used at signup.")
    verifier: str | None = Field(
        default=None,
        description="Optional PKCE code verifier. Leave empty unless your signup flow uses PKCE.",
    )


class PasswordResetRequest(BaseModel):
    ticket: str = Field(min_length=1, description="Password reset ticket from the email link.")
    newPassword: str = Field(min_length=8, max_length=128, examples=["NewStr0ngPass#1"])
    confirmPassword: str = Field(min_length=8, max_length=128, examples=["NewStr0ngPass#1"])

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        _passwords_must_match(self.newPassword, self.confirmPassword)
        return self


class PasswordChangeRequest(BaseModel):
    newPassword: str = Field(min_length=8, max_length=128, examples=["NewStr0ngPass#1"])
    confirmPassword: str = Field(min_length=8, max_length=128, examples=["NewStr0ngPass#1"])

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        _passwords_must_match(self.newPassword, self.confirmPassword)
        return self


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str | None = None
    emailVerified: bool
    displayName: str | None = None
    avatarUrl: str | None = None
    roles: list[str] = Field(default_factory=list)
    createdAt: str | None = None


class AuthSessionPublic(BaseModel):
    accessToken: str
    accessTokenExpiresIn: int
    user: UserPublic
    onboardingCompleted: bool = False
    onboardingCompletedAt: str | None = None


class SignupResponseData(BaseModel):
    message: str
    session: AuthSessionPublic | None = None


class MessageData(BaseModel):
    message: str


class LoginResponseData(AuthSessionPublic):
    pass


class MeResponseData(BaseModel):
    user: UserPublic
    onboardingCompleted: bool = False
    onboardingCompletedAt: str | None = None


class HealthData(BaseModel):
    status: str


def success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}
