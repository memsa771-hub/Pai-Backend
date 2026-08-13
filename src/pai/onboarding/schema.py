"""Adaptive onboarding: manual three-step or CV upload."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

Gender = Literal["male", "female", "non_binary", "prefer_not_to_say", "other"]
CurrentStatus = Literal["student", "professional", "other"]
EducationLevel = Literal["high_school", "bachelor", "master", "other"]
OnboardingPath = Literal["manual", "cv"]

DEGREE_FOR_LEVEL: dict[str, str] = {
    "high_school": "High School",
    "bachelor": "Bachelor's",
    "master": "Master's",
    "other": "Other",
}

PATH_CHOICES = [
    {
        "id": "manual",
        "label": "Complete Onboarding",
        "description": "Answer a short three-step profile so PAI can personalize guidance.",
    },
    {
        "id": "cv",
        "label": "Upload My CV",
        "description": "PAI reads your CV, then asks only for missing critical details.",
    },
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


def _linkedin_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = value if value.startswith(("http://", "https://")) else f"https://{value}"
    host = url.split("://", 1)[1].split("/", 1)[0].lower()
    if "linkedin.com" not in host:
        raise ValueError("LinkedIn URL must be a linkedin.com profile link.")
    return url


class ChoosePathRequest(BaseModel):
    path: OnboardingPath


class OnboardingStep1(BaseModel):
    """Basics: who and where you are. Name was collected at signup."""

    dateOfBirth: date = Field(examples=["2004-03-12"])
    nationality: str = Field(min_length=2, max_length=128, examples=["Pakistani"])
    currentCountry: str = Field(min_length=2, max_length=128, examples=["Pakistan"])
    currentCity: str = Field(min_length=2, max_length=128, examples=["Lahore"])
    currentStatus: CurrentStatus
    gender: Gender | None = None
    linkedinUrl: str | None = Field(default=None, max_length=512)

    @field_validator("nationality", "currentCountry", "currentCity", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("linkedinUrl", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value

    @field_validator("dateOfBirth")
    @classmethod
    def dob(cls, value: date) -> date:
        return _reasonable_dob(value)

    @field_validator("linkedinUrl")
    @classmethod
    def linkedin(cls, value: str | None) -> str | None:
        return _linkedin_url(value)


class OnboardingStep2(BaseModel):
    educationLevel: EducationLevel
    institution: str = Field(min_length=2, max_length=256, examples=["Bahria University"])
    degree: str | None = Field(default=None, max_length=128, examples=["BSCS"])
    major: str | None = Field(default=None, max_length=128, examples=["Computer Science"])
    otherLevelLabel: str | None = Field(default=None, max_length=128)
    gpa: float | None = Field(default=None, ge=0, le=4)
    graduationYear: int | None = Field(default=None, ge=1950, le=2100)

    @field_validator("institution", mode="before")
    @classmethod
    def strip_institution(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("degree", "major", "otherLevelLabel", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def degree_or_field(self) -> OnboardingStep2:
        if not self.degree and not self.major:
            raise ValueError("Provide degree or field of study.")
        if self.educationLevel == "other" and not self.otherLevelLabel and not self.degree:
            raise ValueError("Provide otherLevelLabel or degree when educationLevel is other.")
        return self


class OnboardingStep3(BaseModel):
    primaryGoal: str = Field(
        min_length=2,
        max_length=256,
        examples=["MS Computer Science in Germany"],
    )
    studyCountry: str | None = Field(default=None, max_length=128, examples=["Germany"])
    intake: str | None = Field(default=None, max_length=64, examples=["Fall 2027"])
    budget: str | None = Field(default=None, max_length=128, examples=["limited"])
    scholarships: bool | None = None

    @field_validator("primaryGoal", mode="before")
    @classmethod
    def strip_goal(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("studyCountry", "intake", "budget", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value


class OnboardingGapAnswers(BaseModel):
    """Fill only the missing questions after a CV (or leftover manual gaps)."""

    dateOfBirth: date | None = None
    nationality: str | None = None
    currentCountry: str | None = None
    currentCity: str | None = None
    currentStatus: CurrentStatus | None = None
    gender: Gender | None = None
    linkedinUrl: str | None = None
    educationLevel: EducationLevel | None = None
    institution: str | None = None
    degree: str | None = None
    major: str | None = None
    gpa: float | None = Field(default=None, ge=0, le=4)
    graduationYear: int | None = Field(default=None, ge=1950, le=2100)
    primaryGoal: str | None = None
    studyCountry: str | None = None
    intake: str | None = None
    budget: str | None = None
    scholarships: bool | None = None
    acceptCandidateIds: list[UUID] = Field(default_factory=list)

    @field_validator(
        "nationality",
        "currentCountry",
        "currentCity",
        "linkedinUrl",
        "institution",
        "degree",
        "major",
        "primaryGoal",
        "studyCountry",
        "intake",
        "budget",
        mode="before",
    )
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value

    @field_validator("dateOfBirth")
    @classmethod
    def dob(cls, value: date | None) -> date | None:
        return _reasonable_dob(value) if value else None

    @field_validator("linkedinUrl")
    @classmethod
    def linkedin(cls, value: str | None) -> str | None:
        return _linkedin_url(value)


STEP_META: dict[int, dict[str, object]] = {
    1: {
        "title": "About you",
        "requiredFields": [
            "dateOfBirth",
            "nationality",
            "currentCountry",
            "currentCity",
            "currentStatus",
        ],
        "optionalFields": ["gender", "linkedinUrl"],
    },
    2: {
        "title": "Education",
        "requiredFields": ["educationLevel", "institution", "degreeOrField"],
        "optionalFields": ["gpa", "graduationYear"],
    },
    3: {
        "title": "Your goal",
        "requiredFields": ["primaryGoal"],
        "optionalFields": ["studyCountry", "intake", "budget", "scholarships"],
    },
}
