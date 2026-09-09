"""Record actual analysis inputs; never infer relevance from goal type."""

# Serialization aliases, not rules about what matters to a goal.
ALIASES = {"workExperiences": "work_experiences"}

# Catalog field keys (chat apply) → snapshot keys recorded in freshness.dependencies.
_CATALOG_TO_SNAPSHOT = {
    "career.work_history": "work_experiences",
    "career.projects": "projects",
    "career.skills": "skills",
    "career.certifications": "certifications",
    "application.test_scores": "testAttempts",
}


def input_snapshot(records: dict) -> dict:
    return {ALIASES.get(key, key): value for key, value in records.items()
            if key not in {"counts", "sparseFields", "goals"}}

def recorded_dependencies(snapshot: dict) -> list[str]:
    dependencies = set(snapshot)
    for key, value in snapshot.items():
        if isinstance(value, list):
            dependencies.update(f"{key}:{row['id']}" for row in value
                                if isinstance(row, dict) and row.get("id"))
    return sorted(dependencies)

def _canonical_change(changed: str) -> str:
    if changed.startswith("education."):
        return "educations"
    return _CATALOG_TO_SNAPSHOT.get(changed, changed)


def affects(dependencies: list[str] | None, changed: str) -> bool:
    if not dependencies:
        return True  # Legacy/failed analysis has no reliable input manifest.
    for key in (changed, _canonical_change(changed)):
        if key in dependencies or any(item.startswith((key + ":", key + ".")) for item in dependencies):
            return True
    return False
