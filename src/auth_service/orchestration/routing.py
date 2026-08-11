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

# Broad student/admissions profile signals (PK + international counseling).
_PROFILE_SIGNALS = re.compile(
    r"("
    r"\b("
    r"gpa|cgpa|grade|marks?|percentage|score|"
    r"ielts|toefl|gre|sat|net|ecat|mdcat|"
    r"degree|bachelor|master|phd|bscs|bsc|bs\b|msc|mbbs|fsc|fa\b|ics|"
    r"pre[\s-]?medical|pre[\s-]?engineering|additional\s+maths?|"
    r"university|college|school|board|graduat|major|program|stream|"
    r"pakistan|islamabad|lahore|karachi|peshawar|rawalpindi|"
    r"fast|nust|giki|uet|lums|iba|comsats|bahria|pieas|"
    r"germany|canada|usa|uk|australia|study abroad|visa|passport|"
    r"budget|euro|usd|\$|scholarship|"
    r"internship|experience|project|skill|python|java|"
    r"apply|application|deadline|intake|admission|semester|"
    r"want to|i want|i completed|i finished|i got|i scored|"
    r"actually|correct|instead|not taken|completed|finished"
    r")\b"
    r"|"
    r"\d{2,4}\s*/\s*\d{2,4}"  # e.g. 877/1100
    r")",
    re.I,
)


def should_extract_facts(message: str) -> bool:
    text = (message or "").strip()
    if len(text) < 2:
        return False
    if _GREETING.match(text):
        return False
    if _EXPLAIN_ONLY.match(text) and not _PROFILE_SIGNALS.search(text):
        return False
    if _PROFILE_SIGNALS.search(text):
        return True
    # Short mark/score statements: "PRE MEDICAL 877/1100" or "3.4"
    if re.search(r"\d+(\.\d+)?", text) and len(text.split()) >= 2:
        return True
    if len(text.split()) >= 8:
        return True
    return False
