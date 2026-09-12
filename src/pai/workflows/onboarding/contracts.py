"""Lightweight onboarding seed. Chat, CV, and later updates enrich the Person Vault."""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator

from pai.domains.student.normalization.geo import coerce_country
from pai.domains.student.normalization.vocab import CurrentStatus, Gender
from pai.workflows.onboarding.catalog import ENUM_LABELS, OnboardingPath, PrimaryGoal
from pai.domains.student.normalization.phone import normalize_phone

PATH_CHOICES = [
    {
        "id": OnboardingPath.manual.value,
        "label": ENUM_LABELS["path"][OnboardingPath.manual.value],
        "description": (
            "A short starting profile so PAI can advise from the first chat. "
            "Deeper facts come from conversation."
        ),
    },
    {
        "id": OnboardingPath.cv.value,
        "label": ENUM_LABELS["path"][OnboardingPath.cv.value],
        "description": (
            "Upload your CV. PAI extracts your profile and unlocks chat — no extra form."
        ),
    },
]

ONBOARDING_PURPOSE = (
    "Onboarding is a lightweight starting profile, not the main way to fill the Person Vault. "
    "Chat, CV/document extraction, and later updates continuously enrich the same Vault."
)

REQUIRED_FIELDS = [
    "dateOfBirth",
    "gender",
    "currentStatus",
    "primaryGoal",
]

CONDITIONAL_FIELDS: list[str] = []

OPTIONAL_FIELDS = [
    "fullName",
    "phone",
    "currentCountry",
    "currentCity",
    "nationality",
]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _reasonable_dob(value: date) -> date:
    today = date.today()
    if value >= today:
        raise ValueError("Date of birth must be in the past.")
    oldest = today - timedelta(days=365 * 100)
    youngest = today - timedelta(days=365 * 13)
    if value < oldest or value > youngest:
        raise ValueError("Date of birth must be for someone between 13 and 100 years old.")
    return value



class OnboardingSubmit(BaseModel):
    """Starting profile seed for PAI personal counselor."""

    model_config = {"extra": "ignore"}

    path: OnboardingPath | None = Field(
        default=None,
        description=(
            "manual (form) or cv (confirm after extract). "
            "Defaults to the path already chosen, else manual."
        ),
    )
    fullName: str | None = Field(
        default=None,
        max_length=256,
        examples=["Ali Khan"],
        description="Optional display/preferred name update.",
    )
    dateOfBirth: date = Field(examples=["2004-03-12"])
    gender: Gender
    currentStatus: CurrentStatus
    primaryGoal: PrimaryGoal
    phone: str | None = Field(
        default=None, min_length=8, max_length=32, examples=["+923001234567"]
    )
    currentCountry: str | None = Field(
        default=None, min_length=2, max_length=2, examples=["PK"]
    )
    currentCity: str | None = Field(
        default=None, min_length=2, max_length=128, examples=["Lahore"]
    )
    nationality: str | None = Field(
        default=None, min_length=2, max_length=2, examples=["PK"]
    )

    @field_validator("nationality", "currentCountry", mode="before")
    @classmethod
    def country_code(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return coerce_country(value)

    @field_validator("fullName", "currentCity", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def phone_e164(self):
        if self.phone:
            self.phone = normalize_phone(self.phone, default_region=self.currentCountry)
        return self

    @field_validator("dateOfBirth")
    @classmethod
    def dob(cls, value: date) -> date:
        return _reasonable_dob(value)

    def resolved_degree(self) -> str | None:
        return None

