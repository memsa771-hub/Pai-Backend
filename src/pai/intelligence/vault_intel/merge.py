"""Merge LLM + booster candidates; prefer higher confidence / corrections."""

from __future__ import annotations

import json
from typing import Any

from pai.orchestration.schemas import VaultCandidate


def _norm_val(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip().lower()


def merge_candidates(*groups: list[VaultCandidate]) -> list[VaultCandidate]:
    best: dict[str, VaultCandidate] = {}
    for group in groups:
        for c in group:
            key = c.field_key
            prev = best.get(key)
            if prev is None:
                best[key] = c
                continue
            # Prefer corrections, then higher confidence, then booster rationale
            score_new = c.confidence + (0.05 if c.is_correction else 0.0)
            score_old = prev.confidence + (0.05 if prev.is_correction else 0.0)
            if "booster:" in (c.rationale_summary or "") and score_new >= score_old - 0.02:
                # Boosters win ties on clear structured fields
                if key in (
                    "education.marks",
                    "education.gpa",
                    "application.study_country",
                    "application.target_universities",
                ):
                    best[key] = c
                    continue
            if score_new > score_old:
                best[key] = c
            elif score_new == score_old and _norm_val(c.value) != _norm_val(prev.value):
                # Keep previous; conflicting same-confidence left to verifier
                pass
    return list(best.values())
