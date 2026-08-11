"""Vault Intelligence: boosters, normalize, source registry."""

from __future__ import annotations

from auth_service.intelligence.vault_intel.boosters import run_deterministic_boosters
from auth_service.intelligence.vault_intel.merge import merge_candidates
from auth_service.intelligence.vault_intel.normalize import normalize_candidates
from auth_service.intelligence.vault_intel.service import VaultIntelligenceService
from auth_service.orchestration.schemas import VaultCandidate


def test_boosters_catch_marks_stream_countries_and_cgpa():
    text = (
        "I completed FSc Pre-Medical 877/1100 in Islamabad. "
        "My CGPA later was 3.35. I want MS AI in Germany and China, targeting FAST and NUST."
    )
    cands, hits = run_deterministic_boosters(text, source_reference="m1")
    keys = {c.field_key for c in cands}
    assert "education.marks" in keys
    assert "education.stream" in keys or "education.program" in keys
    assert "education.gpa" in keys
    assert "application.study_country" in keys
    assert "application.target_universities" in keys
    assert "location.current_city" in keys
    assert "application.career_interest" in keys
    assert "education.marks" in hits


def test_normalize_aliases_and_marks_string():
    raw = [
        VaultCandidate(
            field_key="education.cgpa",
            value=3.4,
            confidence=0.9,
            evidence_text="cgpa 3.4",
            source_reference="m1",
        ),
        VaultCandidate(
            field_key="education.marks",
            value="847/1100",
            confidence=0.9,
            evidence_text="847/1100",
            source_reference="m1",
        ),
        VaultCandidate(
            field_key="not.a.field",
            value="x",
            confidence=0.9,
            evidence_text="x",
            source_reference="m1",
        ),
    ]
    out = normalize_candidates(raw)
    keys = {c.field_key for c in out}
    assert "education.gpa" in keys
    assert "education.marks" in keys
    assert "not.a.field" not in keys
    marks = next(c for c in out if c.field_key == "education.marks")
    assert marks.value["obtained"] == 847.0
    assert marks.value["total"] == 1100.0


def test_merge_prefers_booster_on_marks():
    llm = VaultCandidate(
        field_key="education.marks",
        value={"obtained": 800, "total": 1100},
        confidence=0.85,
        evidence_text="approx",
        source_reference="m1",
        rationale_summary="llm",
    )
    booster = VaultCandidate(
        field_key="education.marks",
        value={"obtained": 877, "total": 1100},
        confidence=0.93,
        evidence_text="877/1100",
        source_reference="m1",
        rationale_summary="booster:marks_ratio",
    )
    merged = merge_candidates([llm], [booster])
    assert len(merged) == 1
    assert merged[0].value["obtained"] == 877


def test_vault_intel_registers_future_sources(test_settings):
    from auth_service.llm.gateway import LLMGateway

    gw = LLMGateway(test_settings)
    svc = VaultIntelligenceService(gw)
    sources = svc.registered_sources()
    assert "chat" in sources
    assert "document" in sources
    assert "linkedin" in sources
    assert "social" in sources
