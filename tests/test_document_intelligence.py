from pai.services.document_intelligence.classification.taxonomy import evidence_eligible
from pai.services.document_intelligence.identity.names import names_match
from pai.services.document_intelligence.reconciliation.engine import ReconcileInput, reconcile
from pai.services.document_intelligence.security.validation import sniff_mime
from pai.services.documents.policy import classify_document_type, vault_extraction_policy


def test_generated_docs_are_not_evidence():
    assert evidence_eligible(source_type="ai_generated", document_type="resume") is False
    assert evidence_eligible(source_type="onboarding", document_type="sop") is False
    assert evidence_eligible(source_type="document_vault", document_type="transcript") is True
    assert vault_extraction_policy("ai_generated") == "disabled"


def test_identity_mismatch_is_deterministic():
    assert names_match("Musawir Khan", "Musawir Khan") == "matched"
    assert names_match("Musawir Khan", "Ahmed Khan") == "mismatch"


def test_gpa_critical_conflict_does_not_auto_apply():
    result = reconcile(
        ReconcileInput(
            field_key="education.gpa",
            incoming_value={"value": 3.5, "scale": 4.0, "type": "cumulative"},
            existing_value={"value": 2.5, "scale": 4.0, "type": "cumulative"},
            evidence_text="CGPA: 3.50 / 4.00",
            source_authority="high",
            field_criticality="critical",
            extraction_confidence=0.97,
            document_quality="good",
        )
    )
    assert result.decision == "CRITICAL_CONFLICT"


def test_new_safe_non_critical_can_apply():
    result = reconcile(
        ReconcileInput(
            field_key="career.skills",
            incoming_value=[{"name": "Python"}],
            existing_value=None,
            evidence_text="Skills: Python",
            source_authority="medium",
            field_criticality="normal",
            extraction_confidence=0.95,
            document_quality="good",
        )
    )
    assert result.decision == "NEW_SAFE_FACT"


def test_no_evidence_span_is_insufficient():
    result = reconcile(
        ReconcileInput(
            field_key="education.gpa",
            incoming_value=3.5,
            evidence_text="",
            source_authority="high",
            field_criticality="critical",
            extraction_confidence=0.99,
        )
    )
    assert result.decision == "INSUFFICIENT_EVIDENCE"


def test_sniff_rejects_spoofed_pdf_header():
    assert sniff_mime(b"%PDF-1.4 hello", "x.pdf") == "application/pdf"
    assert sniff_mime(b"\xff\xd8\xff\xdb", "x.jpg") == "image/jpeg"
    assert sniff_mime(b"just text about a cv", "cv.txt") == "text/plain"


def test_likely_match_cannot_auto_apply():
    result = reconcile(
        ReconcileInput(
            field_key="career.skills",
            incoming_value=[{"name": "Python"}],
            existing_value=None,
            evidence_text="Skills: Python",
            source_authority="medium",
            identity_status="likely_match",
            field_criticality="normal",
            extraction_confidence=0.95,
            document_quality="good",
        )
    )
    assert result.decision == "REQUIRES_CONFIRMATION"


def test_classify_uses_ocr_text_when_filename_is_generic():
    from pai.services.document_intelligence.classification.taxonomy import classify_from_name
    from pai.services.document_intelligence.classification.taxonomy import type_meta
    from pai.services.documents.policy import classify_document_type

    assert classify_document_type("passport-scan.png") == "passport"
    assert classify_from_name("scan.jpg") == "other"
    assert classify_from_name("scan.jpg", text="Republic of Pakistan Passport") == "passport"
    assert classify_from_name("scan.jpg", hint="resume", text="Official Transcript CGPA") == "transcript"
    assert classify_from_name("x.pdf", text="statement of purpose") == "sop"
    assert type_meta("transcript")["extractor"] == "transcript"
    assert type_meta("lor")["party_roles"] == ["subject", "author"]


def test_transcript_gpa_shape_attaches_to_education_payload():
    from pai.ingestion.typed_apply import _education_payload

    payload = _education_payload({"value": 3.5, "scale": 4.0, "type": "cumulative"})
    assert payload is not None
    assert payload["gpa"] == 3.5
    assert payload["gpa_scale"] == 4.0
    assert "institution" not in payload


def test_deepseek_vision_is_the_ocr_provider():
    from types import SimpleNamespace

    from pai.services.document_intelligence.providers.deepseek_vision import (
        DeepSeekVisionProvider,
        _images_for_vision,
    )
    from pai.services.document_intelligence.providers.factory import ocr_provider

    settings = SimpleNamespace(
        deepseek_api_key="sk-test",
        document_ocr_provider="deepseek_vision",
        llm_document_vision_model="deepseek-v4-flash-vision-exp",
        document_vision_max_pages=4,
        document_processing_timeout_seconds=120,
        llm_timeout_seconds=60,
        deepseek_base_url="https://api.deepseek.com/v1",
    )
    provider = ocr_provider(settings)
    assert isinstance(provider, DeepSeekVisionProvider)
    assert provider.configured() is True
    jpeg = b"\xff\xd8\xff" + b"\x00" * 9000
    parts = _images_for_vision(jpeg, "image/jpeg", max_pages=4)
    assert parts == [("image/jpeg", jpeg)]
    native = ocr_provider(SimpleNamespace(document_ocr_provider="native"))
    assert native.name == "native"
    settings.deepseek_api_key = ""
    assert DeepSeekVisionProvider(settings).configured() is False
