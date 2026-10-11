"""PII Exposure Reporting & Traceability Audit Module (Member 5 - Role 03).

Surfaces PII exposure to Cadence internal audit:
- Per-file summary of what PII was found
- Counts by PII category and sensitivity tier
- Overall document risk level (CRITICAL, HIGH, MEDIUM, LOW, NONE)
- Separate traceability log kept isolated from downstream LLM input
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Union

from src.common.schema import Document, PIIEntity, PIIFinding, Redaction

HIGH_SENSITIVITY_TYPES = {
    "US_SSN",
    "SSN",
    "GOVERNMENT_ID",
    "GOV_ID",
    "PAN",
    "CREDIT_CARD",
    "ACCOUNT_NUMBER",
    "DATE_OF_BIRTH",
    "DOB",
}

MEDIUM_SENSITIVITY_TYPES = {
    "EMPLOYEE_ID",
    "EMP_ID",
    "PERSON",
    "FULL_NAME",
    "EMAIL_ADDRESS",
    "EMAIL",
    "PHONE_NUMBER",
    "PHONE",
    "ADDRESS",
}


def compute_risk_level(counts_by_type: Dict[str, int], low_conf_ocr_blocks: int = 0) -> str:
    """Determines Cadence audit risk level based on PII types, volume, and OCR confidence."""
    total = sum(counts_by_type.values())
    if total == 0 and low_conf_ocr_blocks == 0:
        return "NONE"

    high_count = sum(
        cnt for p_type, cnt in counts_by_type.items() if p_type.upper() in HIGH_SENSITIVITY_TYPES
    )
    if high_count >= 2 or total >= 10:
        return "CRITICAL"
    if high_count >= 1 or total >= 4 or low_conf_ocr_blocks > 0:
        return "HIGH"
    if total >= 1:
        return "MEDIUM"
    return "LOW"


def generate_exposure_report(
    document: Document,
    entities: Optional[List[Union[PIIEntity, PIIFinding, Dict[str, Any]]]] = None,
    redactions: Optional[List[Redaction]] = None,
    traceability_log: Optional[List[Dict[str, Any]]] = None,
    redacted_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates a comprehensive PII Exposure Report for Cadence internal audit (Role 03)."""
    entities = entities or []
    redactions = redactions or []
    traceability_log = traceability_log or []

    type_counter: Counter = Counter()
    if redactions:
        for r in redactions:
            type_counter[r.entity_type] += 1
    else:
        for e in entities:
            e_type = e.get("entity_type", "PII") if isinstance(e, dict) else getattr(e, "entity_type", "PII")
            type_counter[e_type] += 1

    counts_by_type = dict(type_counter)
    total_pii = sum(counts_by_type.values())
    low_conf_blocks = document.metadata.get("low_confidence_block_ids", [])
    risk_level = compute_risk_level(counts_by_type, len(low_conf_blocks))

    safe_llm_text = redacted_text if redacted_text is not None else "\n\n".join(
        b.text for b in document.blocks if b.text
    )

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "risk_level": risk_level,
        "total_pii_found": total_pii,
        "total_redactions_applied": len(redactions) if redactions else total_pii,
        "counts_by_type": counts_by_type,
        "low_confidence_ocr_blocks": low_conf_blocks,
        "llm_ready": True,
        "safe_text_for_llm": safe_llm_text,
        "traceability_log": traceability_log,
        "audit_summary": (
            f"File '{document.filename}' ({document.file_type.upper()}): "
            f"Identified and redacted {total_pii} PII instance(s) across "
            f"{len(counts_by_type)} category(s). Risk Level: {risk_level}."
        ),
    }


class ExposureReporter:
    """Object-oriented wrapper for generating per-file and batch PII exposure reports."""

    def generate(
        self,
        document: Document,
        entities: Optional[List[Any]] = None,
        redactions: Optional[List[Redaction]] = None,
        traceability_log: Optional[List[Dict[str, Any]]] = None,
        redacted_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        return generate_exposure_report(
            document=document,
            entities=entities,
            redactions=redactions,
            traceability_log=traceability_log,
            redacted_text=redacted_text,
        )


# Standard aliases for pipeline compatibility
create_report = generate_exposure_report
build_report = generate_exposure_report