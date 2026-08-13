"""Onboarding: one complete payload, or CV extract then confirm missing criticals."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from pai.schemas import _normalize_phone

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
        "description": "Fill in your profile. The frontend may show this as steps; PAI stores it in one submit.",
    },
    {
        "id": "cv",
        "label": "Upload My CV",
        "description": "PAI reads your CV/PDF, then you confirm any missing critical fields.",
    },
]

REQUIRED_FIELDS = [
    "phone",
    "dateOfBirth",
    "nationality",
    "currentCountry",
    "currentCity",
    "currentStatus",
    "educationLevel",
    "institution",
    "degreeOrField",
    "primaryGoal",
]

OPTIONAL_FIELDS = [
    "gender",
    "linkedinUrl",
    "gpa",
    "graduationYear",
    "skills",
    "workExperience",
    "targetCountries",
    "studyCountry",
    "intake",
    "budget",
    "scholarships",
    "testScores",
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


class OnboardingSkillItem(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    proficiency: str | None = Field(default=None, max_length=64)

    @field_validator("name", "proficiency", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value


class OnboardingWorkItem(BaseModel):
    organization: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=256)
    employmentType: str | None = Field(default=None, max_length=64)
    isCurrent: bool = False
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("organization", "title", "employmentType", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value


class OnboardingTestScoreItem(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["IELTS"])
    score: str = Field(min_length=1, max_length=64, examples=["7.5"])

    @field_validator("name", "score", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value


class OnboardingSubmit(BaseModel):
    """Complete onboarding payload. Frontend may collect this across UI steps."""

    path: OnboardingPath | None = Field(
        default=None,
        description="manual (form) or cv (confirm after extract). Defaults to the path already chosen, else manual.",
    )
    phone: str = Field(min_length=8, max_length=32, examples=["+923001234567"])
    dateOfBirth: date = Field(examples=["2004-03-12"])
    nationality: str = Field(min_length=2, max_length=128, examples=["Pakistani"])
    currentCountry: str = Field(min_length=2, max_length=128, examples=["Pakistan"])
    currentCity: str = Field(min_length=2, max_length=128, examples=["Lahore"])
    currentStatus: CurrentStatus
    educationLevel: EducationLevel
    institution: str = Field(min_length=2, max_length=256, examples=["Bahria University"])
    degree: str | None = Field(default=None, max_length=128, examples=["BSCS"])
    major: str | None = Field(default=None, max_length=128, examples=["Computer Science"])
    otherLevelLabel: str | None = Field(default=None, max_length=128)
    primaryGoal: str = Field(
        min_length=2,
        max_length=256,
        examples=["MS Computer Science in Germany"],
    )
    gender: Gender | None = None
    linkedinUrl: str | None = Field(default=None, max_length=512)
    gpa: float | None = Field(default=None, ge=0, le=4)
    graduationYear: int | None = Field(default=None, ge=1950, le=2100)
    skills: list[OnboardingSkillItem] = Field(default_factory=list)
    workExperience: list[OnboardingWorkItem] = Field(default_factory=list)
    targetCountries: list[str] = Field(default_factory=list)
    studyCountry: str | None = Field(default=None, max_length=128, examples=["Germany"])
    intake: str | None = Field(default=None, max_length=64, examples=["Fall 2027"])
    budget: str | None = Field(default=None, max_length=128, examples=["limited"])
    scholarships: bool | None = None
    testScores: list[OnboardingTestScoreItem] = Field(default_factory=list)

    @field_validator(
        "nationality",
        "currentCountry",
        "currentCity",
        "institution",
        "primaryGoal",
        mode="before",
    )
    @classmethod
    def strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "degree",
        "major",
        "otherLevelLabel",
        "linkedinUrl",
        "studyCountry",
        "intake",
        "budget",
        mode="before",
    )
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value) if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, value: str) -> str:
        return _normalize_phone(value)

    @field_validator("dateOfBirth")
    @classmethod
    def dob(cls, value: date) -> date:
        return _reasonable_dob(value)

    @field_validator("linkedinUrl")
    @classmethod
    def linkedin(cls, value: str | None) -> str | None:
        return _linkedin_url(value)

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        out: list[object] = []
        for item in value:
            if isinstance(item, str):
                name = item.strip()
                if name:
                    out.append({"name": name})
            else:
                out.append(item)
        return out

    @field_validator("targetCountries", mode="before")
    @classmethod
    def coerce_countries(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return value

    @model_validator(mode="after")
    def degree_or_field(self) -> OnboardingSubmit:
        if self.educationLevel == "high_school":
            return self
        if self.degree or self.major:
            return self
        if self.educationLevel == "other" and self.otherLevelLabel:
            return self
        raise ValueError("Provide degree or field of study.")

    def resolved_degree(self) -> str | None:
        if self.degree:
            return self.degree
        if self.educationLevel == "other" and self.otherLevelLabel:
            return self.otherLevelLabel
        if self.major:
            return None
        return DEGREE_FOR_LEVEL.get(self.educationLevel)
