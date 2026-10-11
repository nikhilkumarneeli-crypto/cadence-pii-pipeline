"""Cadence Text Analysis & PII Detection — Interactive Demo UI (Member 5).

Run with:
    python -m streamlit run app/demo.py
"""

from __future__ import annotations

import html
import re
import sys
import tempfile
from pathlib import Path
from typing import List

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.common.schema import Document, PIIEntity
from src.redaction.redactor import redact_document
from src.redaction.report import generate_exposure_report
from src.router import route_and_extract

FALLBACK_PATTERNS = [
    ("EMPLOYEE_ID", re.compile(r"\bEMP-\d{4,7}\b")),
    ("EMAIL_ADDRESS", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("US_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("GOVERNMENT_ID", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("PHONE_NUMBER", re.compile(r"(?:\+\d{1,2}-)?\d{3}-\d{3}-\d{4}\b")),
    ("DATE_OF_BIRTH", re.compile(r"\b\d{2}/\d{2}/\d{4}\b")),
]


def detect_entities_for_demo(doc: Document) -> List[PIIEntity]:
    """Uses Member 4's detection engine if available, otherwise runs built-in regex recognizers."""
    try:
        import src.detection.engine as det_mod
        for fn_name in ("detect_pii_in_document", "detect_document", "detect"):
            if hasattr(det_mod, fn_name):
                res = getattr(det_mod, fn_name)(doc)
                if isinstance(res, list) and res:
                    return res
    except Exception:
        pass

    entities: List[PIIEntity] = []
    for block in doc.blocks:
        for e_type, pattern in FALLBACK_PATTERNS:
            for match in pattern.finditer(block.text):
                entities.append(
                    PIIEntity(
                        entity_type=e_type,
                        text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.98,
                        block_id=block.block_id,
                        metadata={"detector": "regex_recognizer"},
                    )
                )
    return entities


def highlight_pii_html(raw_text: str, entities: List[PIIEntity]) -> str:
    """Renders highlighted PII spans in HTML for visual inspection."""
    escaped = html.escape(raw_text)
    for e in sorted({(ent.text, ent.entity_type) for ent in entities}, key=lambda x: -len(x[0])):
        pii_val, pii_type = html.escape(e[0]), html.escape(e[1])
        badge = (
            f"<mark style='background:#fde68a;padding:2px 5px;border-radius:4px;font-weight:600;'>"
            f"{pii_val} <span style='font-size:0.75em;color:#b45309;'>({pii_type})</span></mark>"
        )
        escaped = escaped.replace(pii_val, badge)
    return f"<div style='white-space:pre-wrap;font-family:monospace;line-height:1.5;'>{escaped}</div>"


def main() -> None:
    st.set_page_config(page_title="Cadence PII Detection & Redaction Pipeline", layout="wide")
    st.title("Cadence Financial — Artifact PII Detection & Redaction Gateway")
    st.caption("Optiv Consulting | Case Study 2: Upload DOCX, PDF (Digital/Scanned), or PPTX Evidence Artifacts")

    uploaded_files = st.file_uploader(
        "Upload Evidence Artifacts (.docx, .pdf, .pptx)",
        type=["docx", "pdf", "pptx"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("Upload one or more evidence artifacts above to extract text, highlight PII, redact with transparent tags, and generate the internal audit exposure report.")
        return

    for up_file in uploaded_files:
        st.divider()
        st.subheader(f"Artifact: `{up_file.name}`")
        suffix = Path(up_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(up_file.getbuffer())
            tmp_path = Path(tmp.name)

        try:
            doc = route_and_extract(tmp_path)
            doc.filename = up_file.name
        except Exception as exc:
            st.error(f"Extraction error for {up_file.name}: {exc}")
            continue

        entities = detect_entities_for_demo(doc)
        redactions, redacted_text, _, trace_log = redact_document(doc, entities)
        report = generate_exposure_report(
            document=doc,
            entities=entities,
            redactions=redactions,
            traceability_log=trace_log,
            redacted_text=redacted_text,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Extracted Blocks", len(doc.blocks))
        c2.metric("Total PII Detected", report["total_pii_found"])
        c3.metric("Redactions Applied", report["total_redactions_applied"])
        c4.metric("Audit Risk Level", report["risk_level"])

        tab1, tab2, tab3, tab4 = st.tabs([
            "1. Extracted Text & Highlighted PII",
            "2. Safe Redacted Output (For LLM)",
            "3. Audit Exposure Summary",
            "4. Source Traceability Log",
        ])

        full_raw_text = "\n\n".join(f"[{b.block_id}] {b.text}" for b in doc.blocks if b.text)
        with tab1:
            st.markdown(highlight_pii_html(full_raw_text, entities), unsafe_allow_html=True)

        with tab2:
            st.code(report["safe_text_for_llm"], language="text")

        with tab3:
            st.write(report["audit_summary"])
            if report["counts_by_type"]:
                st.table(
                    [{"PII Category": k, "Count": v} for k, v in report["counts_by_type"].items()]
                )

        with tab4:
            if trace_log:
                st.dataframe(trace_log, use_container_width=True)
            else:
                st.write("No PII entities detected.")


if __name__ == "__main__":
    main()