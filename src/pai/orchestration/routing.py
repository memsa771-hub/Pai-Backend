from __future__ import annotations

import re

from pai.config import Settings

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|ok(?:ay)?|please continue|got it|"
    r"sure|yep|yes|no|help|help me|what now|continue)\s*[!.?]*\s*$",
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
# Live lookup only — not "what should I do next?"
_LIVE_WEB = re.compile(
    r"\b("
    r"ielts|toefl|pte|gre|gmat|sat\b|act\b|emsat|"
    r"deadline|deadlines|intake|intakes|tuition|ranking|rankings|"
    r"visa|scholarship|scholarships|cut[- ]?off|"
    r"acceptance\s+rate|qs\b|fees|"
    r"latest|this year|20(2[5-9]|3[0-9])"
    r")\b",
    re.I,
)


def _has_profile_signal(text: str) -> bool:
    return bool(_SELF_FACT.search(text) or _PROFILE_HINT.search(text))


def should_extract_facts(message: str) -> bool:
    """Skip the extract LLM unless this turn can contain new personal facts."""
    text = (message or "").strip()
    if len(text) < 2:
        return False
    if _GREETING.match(text):
        return False
    if _EXPLAIN_ONLY.match(text):
        return False
    has_fact = _has_profile_signal(text)
    if "?" in text and not has_fact:
        return False
    if _ADVICE_LEAD.match(text) and not has_fact:
        return False
    if has_fact:
        return True
    # Short chit-chat ("help me plan", "ok go") is counselor-only.
    if len(text.split()) <= 8:
        return False
    return True


def counselor_needs_live_web(message: str) -> bool:
    """Tavily only for live requirements / rankings — not for advice or profile."""
    text = (message or "").strip()
    if len(text) < 8:
        return False
    if _GREETING.match(text):
        return False
    if not ("?" in text or _ADVICE_LEAD.match(text)):
        return False
    return bool(_LIVE_WEB.search(text))


def counselor_web_search_enabled(settings: Settings, message: str | None = None) -> bool:
    """Offer Tavily when configured and this turn actually needs live web facts."""
    if not (settings.enable_counselor_tools and (settings.tavily_api_key or "").strip()):
        return False
    if message is None:
        return True
    return counselor_needs_live_web(message)
