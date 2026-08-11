from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class SignupRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["Str0ngPass#1"])


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


class PasswordChangeRequest(BaseModel):
    newPassword: str = Field(min_length=8, max_length=128, examples=["NewStr0ngPass#1"])


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


class SignupResponseData(BaseModel):
    message: str
    session: AuthSessionPublic | None = None


class MessageData(BaseModel):
    message: str


class LoginResponseData(AuthSessionPublic):
    pass


class MeResponseData(BaseModel):
    user: UserPublic


class HealthData(BaseModel):
    status: str


def success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}
