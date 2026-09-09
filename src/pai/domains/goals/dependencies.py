"""Record actual analysis inputs; never infer relevance from goal type."""

# Serialization aliases, not rules about what matters to a goal.
ALIASES = {"workExperiences": "work_experiences"}

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

def affects(dependencies: list[str] | None, changed: str) -> bool:
    if not dependencies:
        return True  # Legacy/failed analysis has no reliable input manifest.
    if changed in dependencies:
        return True
    key = changed
    return key in dependencies or any(item.startswith((key + ":", key + ".")) for item in dependencies)
