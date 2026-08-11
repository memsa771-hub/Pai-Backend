from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

PROMPTS_DIR = Path(__file__).resolve().parent

REQUIRED_VARS: dict[str, set[str]] = {
    "fact_extraction.v1.jinja2": {
        "message_id",
        "user_message",
        "source_type",
        "catalog_hint",
    },
    "student_conversation.v1.jinja2": {
        "current_message",
        "student_context",
        "semantic_memory_context",
        "pending_confirmations",
        "applied_vault_changes",
        "task_results",
    },
    "system.v1.jinja2": set(),
}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(name: str, **kwargs: object) -> str:
    return _env().get_template(name).render(**kwargs)


def validate_prompt_templates() -> None:
    env = _env()
    for name, required in REQUIRED_VARS.items():
        path = PROMPTS_DIR / name
        if not path.is_file():
            raise TemplateNotFound(name)
        source = path.read_text(encoding="utf-8")
        env.from_string(source)
        for var in required:
            if f"{{{{ {var}" not in source and f"{{{{ {var} }}" not in source:
                raise ValueError(f"Prompt {name} missing required variable {var}")
