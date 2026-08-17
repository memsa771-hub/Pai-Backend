from __future__ import annotations

import re

from pai.config import Settings

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|ok(?:ay)?(?:\s+go)?|please continue|"
    r"got it|sure|yep|yes|no|help|help me|what now|continue|go ahead|alright)"
    r"\s*[!.?]*\s*$",
    re.I,
)
_EXPLAIN_ONLY = re.compile(
    r"^\s*(can you explain|what do you mean|could you clarify|help me understand).*\??\s*$",
    re.I,
)
_SELF_FACT = re.compile(
    r"\b("
    r"i am|i'm|i live|i want|i have|i got|i scored|i completed|i finished|"
    r"i study|i studied|i prefer|i'm from|i am from|my gpa|my cgpa|my budget|"
    r"my name|i moved"
    r")\b",
    re.I,
)
_PROFILE_HINT = re.compile(
    r"\d{2,4}\s*/\s*\d{2,4}"
    r"|additional\s+maths"
    r"|\b(?:gpa|cgpa|emsat)\b"
    r"|\b(pre[\s-]?medical|pre[\s-]?engineering|bscs|a[\s-]?levels?)\b",
    re.I,
)
_ADVICE_LEAD = re.compile(
    r"^\s*(what|which|when|where|how|who|latest|current|can you|could you|please)\b",
    re.I,
)


def _has_profile_signal(text: str) -> bool:
    return bool(_SELF_FACT.search(text) or _PROFILE_HINT.search(text))


def should_extract_facts(message: str) -> bool:
    """Extract statements. Skip greetings, acknowledgements, and advice-only questions."""
    text = (message or "").strip()
    if len(text) < 2:
        return False
    if _GREETING.match(text):
        return False
    if _EXPLAIN_ONLY.match(text):
        return False
    asking = "?" in text or bool(_ADVICE_LEAD.match(text))
    if asking and not _has_profile_signal(text):
        return False
    return True


def counselor_web_search_enabled(settings: Settings, message: str | None = None) -> bool:
    """Offer live web whenever the counselor has tools. Usage is the model's job.

    Gating the *tool* off by keyword made PAI claim it had no web access on
    research turns. Greetings stay tool-off so "hi" is one LLM call.
    """
    if not (settings.enable_counselor_tools and (settings.tavily_api_key or "").strip()):
        return False
    if message is None:
        return True
    text = (message or "").strip()
    if len(text) < 2 or _GREETING.match(text):
        return False
    return True
