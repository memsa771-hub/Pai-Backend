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


def should_extract_facts(message: str) -> bool:
    """Run Vault Intelligence unless this turn cannot contain new personal facts.

    Country/university/test keyword lists are not used — the extraction agent
    returns [] when there is nothing to write. Greetings and pure clarify
    turns skip the extra LLM call.
    """
    text = (message or "").strip()
    if len(text) < 2:
        return False
    if _GREETING.match(text):
        return False
    if _EXPLAIN_ONLY.match(text):
        return False
    return True
