"""Unit and integration tests for Member 5 (Redaction, Exposure Report, Pipeline Contract)."""

from __future__ import annotations

from src.common.schema import Document, PIIEntity, TextBlock
from src.redaction.redactor import PIIRedactor, redact, redact_document, redact_text
from src.redaction.report import compute_risk_level, generate_exposure_report


def _build_sample_doc() -> Document:
    blocks = [
        TextBlock(
            block_id="para_0",
            text="Primary Approver: Vikramaditya Rao (Employee ID: EMP-77210)",
            page_number=1,
            metadata={"block_type": "paragraph", "position": {"left": 50.0, "top": 100.0}},
        ),
        TextBlock(
            block_id="para_1",
            text="Email: vikram.rao@cadencebank.com | SSN: 412-88-9021 | Contact Vikramaditya Rao",
            page_number=1,
            metadata={"block_type": "paragraph", "position": {"left": 50.0, "top": 130.0}},
        ),
    ]
    return Document(
        document_id="doc_audit_sample",
        filename="audit_sample.pdf",
        file_type="pdf",
        blocks=blocks,
        metadata={"page_count": 1},
    )


def test_redact_text_sequential_and_consistent_tags() -> None:
    raw = "Contact Alice Smith at alice@cadence.com or Alice Smith at +1-212-555-0199."
    entities = [
        PIIEntity(entity_type="PERSON", text="Alice Smith", start=8, end=19),
        PIIEntity(entity_type="EMAIL_ADDRESS", text="alice@cadence.com", start=23, end=40),
        PIIEntity(entity_type="PERSON", text="Alice Smith", start=44, end=55),
        PIIEntity(entity_type="PHONE_NUMBER", text="+1-212-555-0199", start=59, end=74),
    ]
    redactions, redacted_str = redact_text(raw, entities)
    assert "Alice Smith" not in redacted_str
    assert "alice@cadence.com" not in redacted_str
    assert "+1-212-555-0199" not in redacted_str
    assert redacted_str.count("[PERSON_01]") == 2
    assert "[EMAIL_01]" in redacted_str
    assert "[PHONE_01]" in redacted_str
    assert len(redactions) == 4


def test_pipeline_redactor_contract() -> None:
    """Verifies PIIRedactor.redact() returns (List[Redaction], str) expected by PIIPipeline."""
    doc = _build_sample_doc()
    entities = [
        PIIEntity(entity_type="PERSON", text="Vikramaditya Rao", start=18, end=34, block_id="para_0"),
        PIIEntity(entity_type="EMPLOYEE_ID", text="EMP-77210", start=49, end=58, block_id="para_0"),
        PIIEntity(entity_type="EMAIL_ADDRESS", text="vikram.rao@cadencebank.com", start=7, end=33, block_id="para_1"),
        PIIEntity(entity_type="US_SSN", text="412-88-9021", start=41, end=52, block_id="para_1"),
        PIIEntity(entity_type="PERSON", text="Vikramaditya Rao", start=63, end=79, block_id="para_1"),
    ]
    redactor = PIIRedactor()
    redactions, redacted_text = redactor.redact(doc, entities)

    assert isinstance(redactions, list)
    assert isinstance(redacted_text, str)
    assert len(redactions) == 5
    assert "Vikramaditya Rao" not in redacted_text
    assert "412-88-9021" not in redacted_text
    assert "[PERSON_01]" in redacted_text
    assert "[EMP_ID_01]" in redacted_text
    assert "[EMAIL_01]" in redacted_text
    assert "[SSN_01]" in redacted_text
    assert len(redactor.last_traceability_log) == 5

    # Verify callable alias redact(doc, entities) also matches pipeline contract
    r_list, r_str = redact(doc, entities)
    assert len(r_list) == 5
    assert "[SSN_01]" in r_str


def test_exposure_report_and_risk_levels() -> None:
    doc = _build_sample_doc()
    entities = [
        PIIEntity(entity_type="PERSON", text="Vikramaditya Rao", start=18, end=34, block_id="para_0"),
        PIIEntity(entity_type="US_SSN", text="412-88-9021", start=41, end=52, block_id="para_1"),
    ]
    redactions, redacted_text, _, trace_log = redact_document(doc, entities)
    report = generate_exposure_report(
        document=doc,
        entities=entities,
        redactions=redactions,
        traceability_log=trace_log,
        redacted_text=redacted_text,
    )

    assert report["total_pii_found"] == 2
    assert report["risk_level"] in ("HIGH", "CRITICAL")
    assert report["counts_by_type"]["PERSON"] == 1
    assert report["counts_by_type"]["US_SSN"] == 1
    assert "412-88-9021" not in report["safe_text_for_llm"]
    assert len(report["traceability_log"]) == 2


def test_risk_level_edge_cases() -> None:
    assert compute_risk_level({}) == "NONE"
    assert compute_risk_level({"EMAIL": 1}) == "MEDIUM"
    assert compute_risk_level({"US_SSN": 1}) == "HIGH"
    assert compute_risk_level({"US_SSN": 2, "PAN": 1}) == "CRITICAL"