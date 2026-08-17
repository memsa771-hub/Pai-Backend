"""Closed vocabularies for onboarding dropdowns (ISO countries + PAI goal paths)."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pai.geo import country_options


class OnboardingPath(StrEnum):
    manual = "manual"
    cv = "cv"


class Gender(StrEnum):
    male = "male"
    female = "female"
    non_binary = "non_binary"
    prefer_not_to_say = "prefer_not_to_say"
    other = "other"


class CurrentStatus(StrEnum):
    student = "student"
    graduate = "graduate"
    professional = "professional"
    job_seeker = "job_seeker"
    other = "other"


class EducationLevel(StrEnum):
    high_school = "high_school"
    diploma = "diploma"
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    other = "other"


class PrimaryGoal(StrEnum):
    exploring = "exploring"
    placement = "placement"
    admission = "admission"
    professional = "professional"
    journey_tracker = "journey_tracker"


class FieldOfStudy(StrEnum):
    computer_science = "computer_science"
    software_engineering = "software_engineering"
    data_science = "data_science"
    artificial_intelligence = "artificial_intelligence"
    engineering = "engineering"
    business = "business"
    medicine = "medicine"
    law = "law"
    arts_humanities = "arts_humanities"
    social_sciences = "social_sciences"
    natural_sciences = "natural_sciences"
    other = "other"


class IntakeSeason(StrEnum):
    fall = "fall"
    spring = "spring"
    summer = "summer"
    winter = "winter"
    rolling = "rolling"


class BudgetBand(StrEnum):
    limited = "limited"
    moderate = "moderate"
    comfortable = "comfortable"
    fully_funded = "fully_funded"


class SkillProficiency(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class EmploymentType(StrEnum):
    internship = "internship"
    part_time = "part_time"
    full_time = "full_time"
    contract = "contract"
    freelance = "freelance"
    other = "other"


class StandardizedTest(StrEnum):
    ielts = "ielts"
    toefl = "toefl"
    pte = "pte"
    duolingo = "duolingo"
    gre = "gre"
    gmat = "gmat"
    sat = "sat"
    act = "act"
    net = "net"
    ecat = "ecat"
    mdcat = "mdcat"
    other = "other"


ENUM_LABELS: dict[str, dict[str, str]] = {
    "path": {
        "manual": "Complete Onboarding",
        "cv": "Upload My CV",
    },
    "gender": {
        "male": "Male",
        "female": "Female",
        "non_binary": "Non-binary",
        "prefer_not_to_say": "Prefer not to say",
        "other": "Other",
    },
    "currentStatus": {
        "student": "Student",
        "graduate": "Graduate",
        "professional": "Working professional",
        "job_seeker": "Job seeker",
        "other": "Other",
    },
    "educationLevel": {
        "high_school": "High school",
        "diploma": "Diploma / intermediate",
        "bachelor": "Bachelor's",
        "master": "Master's",
        "phd": "PhD / doctorate",
        "other": "Other",
    },
    "primaryGoal": {
        "exploring": "Exploring options",
        "placement": "Placement (jobs / internships)",
        "admission": "University admission",
        "professional": "Professional growth",
        "journey_tracker": "Journey tracker",
    },
    "major": {
        "computer_science": "Computer science",
        "software_engineering": "Software engineering",
        "data_science": "Data science",
        "artificial_intelligence": "Artificial intelligence",
        "engineering": "Engineering",
        "business": "Business",
        "medicine": "Medicine",
        "law": "Law",
        "arts_humanities": "Arts & humanities",
        "social_sciences": "Social sciences",
        "natural_sciences": "Natural sciences",
        "other": "Other",
    },
    "intake": {
        "fall": "Fall",
        "spring": "Spring",
        "summer": "Summer",
        "winter": "Winter",
        "rolling": "Rolling",
    },
    "budget": {
        "limited": "Limited",
        "moderate": "Moderate",
        "comfortable": "Comfortable",
        "fully_funded": "Fully funded / seeking full funding",
    },
    "proficiency": {
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "expert": "Expert",
    },
    "employmentType": {
        "internship": "Internship",
        "part_time": "Part-time",
        "full_time": "Full-time",
        "contract": "Contract",
        "freelance": "Freelance",
        "other": "Other",
    },
    "testName": {
        "ielts": "IELTS",
        "toefl": "TOEFL",
        "pte": "PTE",
        "duolingo": "Duolingo",
        "gre": "GRE",
        "gmat": "GMAT",
        "sat": "SAT",
        "act": "ACT",
        "net": "NET",
        "ecat": "ECAT",
        "mdcat": "MDCAT",
        "other": "Other",
    },
}

PRIMARY_GOAL_TITLES = ENUM_LABELS["primaryGoal"]

GOAL_TYPE_FOR_PRIMARY: dict[str, str] = {
    "exploring": "exploration",
    "placement": "career",
    "admission": "application",
    "professional": "career",
    "journey_tracker": "tracking",
}

DEGREE_FOR_LEVEL: dict[str, str] = {
    "high_school": "High School",
    "diploma": "Diploma",
    "bachelor": "Bachelor's",
    "master": "Master's",
    "phd": "PhD",
    "other": "Other",
}


def _options(values: list[str], labels: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"id": value, "label": labels.get(value, value.replace("_", " ").title())}
        for value in values
    ]


@lru_cache(maxsize=1)
def field_enum_catalog() -> dict[str, list[dict[str, str]]]:
    countries = list(country_options())
    return {
        "path": _options([m.value for m in OnboardingPath], ENUM_LABELS["path"]),
        "gender": _options([m.value for m in Gender], ENUM_LABELS["gender"]),
        "currentStatus": _options(
            [m.value for m in CurrentStatus], ENUM_LABELS["currentStatus"]
        ),
        "educationLevel": _options(
            [m.value for m in EducationLevel], ENUM_LABELS["educationLevel"]
        ),
        "primaryGoal": _options([m.value for m in PrimaryGoal], ENUM_LABELS["primaryGoal"]),
        "major": _options([m.value for m in FieldOfStudy], ENUM_LABELS["major"]),
        "intake": _options([m.value for m in IntakeSeason], ENUM_LABELS["intake"]),
        "budget": _options([m.value for m in BudgetBand], ENUM_LABELS["budget"]),
        "proficiency": _options(
            [m.value for m in SkillProficiency], ENUM_LABELS["proficiency"]
        ),
        "employmentType": _options(
            [m.value for m in EmploymentType], ENUM_LABELS["employmentType"]
        ),
        "testName": _options([m.value for m in StandardizedTest], ENUM_LABELS["testName"]),
        "nationality": countries,
        "currentCountry": countries,
        "studyCountry": countries,
        "targetCountries": countries,
    }
