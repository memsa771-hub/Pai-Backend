"""Render already-filtered student facts without loading any department."""
import re
from typing import Any

def _sparse_value(entry: Any) -> Any:
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def build_known_facts(
    *,
    identity: dict[str, Any],
    sparse: dict[str, Any],
    typed: dict[str, Any],
) -> list[str]:
    """Human-readable facts already known — counselor must not re-ask these."""
    facts: list[str] = []
    name = identity.get("preferredName") or identity.get("fullName")
    if name:
        facts.append(f"Student name: {name}")

    for edu in typed.get("educations") or []:
        parts = [
            p
            for p in (
                edu.get("degree"),
                edu.get("major"),
                edu.get("institution"),
            )
            if p
        ]
        detail = " / ".join(str(p) for p in parts) if parts else "education record"
        if edu.get("gpa") is not None:
            scale = edu.get("gpaScale")
            detail += f", GPA/CGPA {edu['gpa']}"
            detail += f"/{scale}" if scale is not None else " (scale unknown)"
        if edu.get("percentage") is not None:
            detail += f", {edu['percentage']}%"
        facts.append(f"Education: {detail}")

    seen_goal_titles: set[str] = set()
    for goal in typed.get("goals") or []:
        title = goal.get("title")
        if not title or goal.get("status") == "archived":
            continue
        key = re.sub(r"\s+", " ", str(title)).strip().casefold()
        if not key or key in seen_goal_titles:
            continue
        seen_goal_titles.add(key)
        facts.append(f"Career/study goal: {title}")

    for skill in (typed.get("skills") or [])[:12]:
        if skill.get("name"):
            facts.append(f"Skill: {skill['name']}")

    for key, label in (
        ("application.study_country", "Target study country/countries"),
        ("application.career_interest", "Career interest"),
        ("application.target_universities", "Target universities"),
        ("application.admission_cycle", "Admission cycle"),
        ("application.test_scores", "Test scores"),
        ("mobility.preferred_regions", "Preferred regions"),
        ("education.stream", "Education stream"),
        ("education.marks", "Marks"),
        ("education.additional_maths", "Additional Maths"),
        ("location.current_city", "Current city"),
        ("location.current_country", "Current country"),
        ("demographics.gender", "Gender"),
        ("demographics.nationality", "Nationality"),
        ("demographics.date_of_birth", "Date of birth"),
        ("identity.current_status", "Current status"),
        ("social.linkedin_url", "LinkedIn"),
        ("education.highest_level", "Highest education level"),
        ("preferences.preferred_language", "Preferred language"),
        ("preferences.learning_style", "Learning style"),
        ("preferences.communication_style", "Communication style"),
        ("finance.funding_status", "Funding / budget status"),
        ("finance.scholarship_interest", "Scholarship interest"),
        ("mobility.relocation_willingness", "Relocation willingness"),
    ):
        if key in sparse:
            raw = _sparse_value(sparse[key])
            if raw in (None, "", "***"):
                continue
            facts.append(f"{label}: {raw}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for f in facts:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


