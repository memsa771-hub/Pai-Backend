"""Request models for the three-step post-login onboarding journey."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Gender = Literal["male", "female", "non_binary", "prefer_not_to_say", "other"]
CurrentStatus = Literal["student", "professional", "other"]
EducationLevel = Literal["high_school", "bachelor", "master", "other"]

STEP_META: dict[int, dict[str, object]] = {
    1: {
        "title": "Identity",
        "requiredFields": ["fullName", "dateOfBirth", "gender", "nationality"],
        "optionalFields": [],
    },
    2: {
        "title": "Location and status",
        "requiredFields": ["currentCountry", "currentCity", "currentStatus"],
        "optionalFields": ["nationalId", "linkedinUrl"],
    },
    3: {
        "title": "Academic background",
        "requiredFields": ["educationLevel", "institution"],
        "optionalFields": ["otherLevelLabel", "degree", "major", "graduationYear"],
    },
}

DEGREE_FOR_LEVEL: dict[str, str] = {
    "high_school": "High School",
    "bachelor": "Bachelor's",
    "master": "Master's",
    "other": "Other",
}


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class OnboardingStep1(BaseModel):
    fullName: str = Field(min_length=2, max_length=256, examples=["Ayesha Khan"])
    dateOfBirth: date = Field(examples=["2004-03-12"])
    gender: Gender
    nationality: str = Field(min_length=2, max_length=128, examples=["Pakistani"])

    @field_validator("fullName", "nationality", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("dateOfBirth")
    @classmethod
    def reasonable_age(cls, value: date) -> date:
        today = date.today()
        if value >= today:
            raise ValueError("Date of birth must be in the past.")
        oldest = today - timedelta(days=365 * 100)
        youngest = today - timedelta(days=365 * 13)
        if value < oldest or value > youngest:
            raise ValueError("Date of birth must be for someone between 13 and 100 years old.")
        return value


class OnboardingStep2(BaseModel):
    currentCountry: str = Field(min_length=2, max_length=128, examples=["Pakistan"])
    currentCity: str = Field(min_length=2, max_length=128, examples=["Lahore"])
    currentStatus: CurrentStatus
    nationalId: str | None = Field(
        default=None,
        max_length=64,
        description="National ID / CNIC when required by the user's country. Optional otherwise.",
        examples=["35202-1234567-1"],
    )
    linkedinUrl: str | None = Field(
        default=None,
        max_length=512,
        examples=["https://www.linkedin.com/in/ayesha-khan"],
    )

    @field_validator("currentCountry", "currentCity", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("nationalId", "linkedinUrl", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return _blank_to_none(value)
        return value

    @field_validator("linkedinUrl")
    @classmethod
    def linkedin_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        url = value if value.startswith(("http://", "https://")) else f"https://{value}"
        host = url.split("://", 1)[1].split("/", 1)[0].lower()
        if "linkedin.com" not in host:
            raise ValueError("LinkedIn URL must be a linkedin.com profile link.")
        return url


class OnboardingStep3(BaseModel):
    educationLevel: EducationLevel
    otherLevelLabel: str | None = Field(default=None, max_length=128)
    institution: str = Field(min_length=2, max_length=256, examples=["Punjab College"])
    degree: str | None = Field(default=None, max_length=128)
    major: str | None = Field(default=None, max_length=128, examples=["Pre-Engineering"])
    graduationYear: int | None = Field(default=None, ge=1950, le=2100)

    @field_validator("institution", mode="before")
    @classmethod
    def strip_institution(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("otherLevelLabel", "degree", "major", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return _blank_to_none(value)
        return value

    @model_validator(mode="after")
    def other_label_when_needed(self) -> OnboardingStep3:
        if self.educationLevel == "other" and not self.otherLevelLabel and not self.degree:
            raise ValueError("Provide otherLevelLabel or degree when educationLevel is other.")
        return self
