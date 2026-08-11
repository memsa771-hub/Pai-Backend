from __future__ import annotations

import re

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|ok(?:ay)?|please continue|got it|sure|yep|yes|no)\s*[!.?]*\s*$",
    re.I,
)
_EXPLAIN_ONLY = re.compile(
    r"^\s*(can you explain|what do you mean|could you clarify|help me understand).*\??\s*$",
    re.I,
)

_PROFILE_SIGNALS = re.compile(
    r"\b("
    r"gpa|cgpa|grade|ielts|toefl|gre|sat|degree|bachelor|master|phd|bsc|bs\b|msc|"
    r"university|college|graduat|major|program|"
    r"germany|canada|usa|uk|australia|study abroad|visa|passport|"
    r"budget|euro|usd|\$|scholarship|"
    r"internship|experience|project|skill|python|java|"
    r"apply|application|deadline|intake|"
    r"actually|correct|instead|not taken|completed|finished"
    r")\b",
    re.I,
)


def should_extract_facts(message: str) -> bool:
    text = (message or "").strip()
    if len(text) < 3:
        return False
    if _GREETING.match(text):
        return False
    if _EXPLAIN_ONLY.match(text) and not _PROFILE_SIGNALS.search(text):
        return False
    if _PROFILE_SIGNALS.search(text):
        return True
    if re.search(r"\d+(\.\d+)?", text) and len(text.split()) >= 4:
        return True
    if len(text.split()) >= 12:
        return True
    return False
