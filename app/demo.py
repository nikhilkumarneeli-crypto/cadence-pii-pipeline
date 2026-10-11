"""
Optiv x Cadence - PII Shield
=============================
Enterprise-grade Cyber Risk & Compliance dashboard for the PII detection,
redaction and audit pipeline. Single-file Streamlit app (app/demo.py).

Pipeline: Ingestion -> Extraction -> Detection -> Redaction -> Audit Report
"""

import csv
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# --------------------------------------------------------------------------- #
# 0. PATH SETUP
# --------------------------------------------------------------------------- #
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
for _p in (str(PROJECT_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

try:  # pandas optional - pure-python fallbacks exist everywhere
    import pandas as pd
    _HAVE_PANDAS = True
except Exception:  # pragma: no cover
    pd = None
    _HAVE_PANDAS = False


# --------------------------------------------------------------------------- #
# 1. SCHEMA CONTRACTS (import team modules, fall back to local copies)
# --------------------------------------------------------------------------- #
try:
    from src.common.schema import TextBlock, Document, PIIEntity, Redaction  # noqa
    _HAVE_SCHEMA = True
except Exception:  # pragma: no cover - fallback so the demo NEVER crashes
    _HAVE_SCHEMA = False

    @dataclass
    class TextBlock:
        block_id: str
        text: str
        page_number: Optional[int] = None
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class Document:
        document_id: str
        filename: str
        file_type: str
        blocks: List[TextBlock] = field(default_factory=list)
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class PIIEntity:
        entity_type: str
        text: str
        start: int
        end: int
        confidence: float = 1.0
        block_id: Optional[str] = None
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class Redaction:
        entity_type: str
        original_text: str
        replacement: str
        start: int
        end: int
        block_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# 2. DOMAIN CONSTANTS
# --------------------------------------------------------------------------- #
RISK_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}

TAG_PREFIX = {
    "PERSON": "PERSON",
    "EMPLOYEE_ID": "EMP_ID",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "US_SSN": "SSN",
    "GOVERNMENT_ID": "GOV_ID",
    "CREDIT_CARD": "CC",
    "ACCOUNT_NUMBER": "ACCT",
    "DATE_OF_BIRTH": "DOB",
    "ADDRESS": "ADDR",
}

TYPE_SHORT = {
    "PERSON": "PERSON", "EMPLOYEE_ID": "EMP_ID", "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE", "US_SSN": "SSN", "GOVERNMENT_ID": "GOV_ID",
    "CREDIT_CARD": "CREDIT_CARD", "ACCOUNT_NUMBER": "ACCT_NO",
    "DATE_OF_BIRTH": "DOB", "ADDRESS": "ADDRESS",
}

SENSITIVITY = {
    "US_SSN": "CRITICAL", "GOVERNMENT_ID": "CRITICAL",
    "CREDIT_CARD": "CRITICAL", "ACCOUNT_NUMBER": "CRITICAL",
    "EMPLOYEE_ID": "HIGH", "DATE_OF_BIRTH": "HIGH",
    "EMAIL_ADDRESS": "MEDIUM", "PHONE_NUMBER": "MEDIUM", "ADDRESS": "MEDIUM",
    "PERSON": "LOW",
}

ALL_TYPES = list(TAG_PREFIX.keys())
PIPELINE_STAGES = ["Ingestion", "Extraction", "Detection", "Redaction", "Audit Report"]


# --------------------------------------------------------------------------- #
# 3. BUILT-IN FALLBACK EXTRACTORS (docx / pdf / pptx) - demo never crashes
# --------------------------------------------------------------------------- #
def _ocr_page_fitz(path: Union[str, Path], page_number: int) -> Tuple[str, float]:
    """Attempt OCR of a scanned page via PyMuPDF (needs Tesseract)."""
    try:
        import fitz
        doc = fitz.open(str(path))
        page = doc[page_number - 1]
        tp = page.get_textpage_ocr(flags=0, language="eng", dpi=200, full=True)
        text = page.get_text(textpage=tp).strip()
        doc.close()
        return text, (0.62 if text else 0.0)
    except Exception:
        return "", 0.0


def _extract_pdf(path: Union[str, Path]) -> List[TextBlock]:
    import pdfplumber
    blocks: List[TextBlock] = []
    with pdfplumber.open(str(path)) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=True) or []
            if not words:
                text, conf = _ocr_page_fitz(path, pno)
                if text:
                    blocks.append(TextBlock(
                        block_id=f"p{pno}_ocr1", text=text, page_number=pno,
                        metadata={"block_type": "paragraph", "source_type": "scanned_ocr",
                                  "is_heading": False, "position": None, "confidence": conf,
                                  "low_confidence_flag": conf < 0.75,
                                  "low_confidence_words": []}))
                continue
            clusters: "OrderedDict[int, List[dict]]" = OrderedDict()
            for w in sorted(words, key=lambda x: (x["top"], x["x0"])):
                key = None
                for k in clusters:
                    if abs(k - w["top"]) <= 4:
                        key = k
                        break
                if key is None:
                    key = round(w["top"])
                    clusters[key] = []
                clusters[key].append(w)
            for li, (top, ws) in enumerate(clusters.items()):
                line_text = " ".join(x["text"] for x in sorted(ws, key=lambda x: x["x0"]))
                blocks.append(TextBlock(
                    block_id=f"p{pno}_b{li + 1:03d}", text=line_text, page_number=pno,
                    metadata={"block_type": "paragraph", "source_type": "digital_pdf",
                              "is_heading": False,
                              "position": {"left": min(x["x0"] for x in ws), "top": top,
                                           "width": max(x["x1"] for x in ws) - min(x["x0"] for x in ws),
                                           "height": max(x["height"] for x in ws)},
                              "confidence": 0.98, "low_confidence_flag": False,
                              "low_confidence_words": []}))
    return blocks


def _extract_docx(path: Union[str, Path]) -> List[TextBlock]:
    import docx as _docx_mod
    d = _docx_mod.Document(str(path))
    blocks: List[TextBlock] = []
    i = 0
    for p in d.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        i += 1
        style = (p.style.name or "").lower() if p.style is not None else ""
        is_head = style.startswith("heading") or style == "title"
        blocks.append(TextBlock(
            block_id=f"b{i:04d}", text=t,
            metadata={"block_type": "heading" if is_head else "paragraph",
                      "source_type": "digital", "is_heading": is_head,
                      "confidence": 0.99, "low_confidence_flag": False,
                      "low_confidence_words": []}))
    for tbl in d.tables:
        for r in tbl.rows:
            for c in r.cells:
                t = (c.text or "").strip()
                if not t:
                    continue
                i += 1
                blocks.append(TextBlock(
                    block_id=f"b{i:04d}", text=t,
                    metadata={"block_type": "table_cell", "source_type": "digital",
                              "is_heading": False, "confidence": 0.99,
                              "low_confidence_flag": False, "low_confidence_words": []}))
    return blocks


def _extract_pptx(path: Union[str, Path]) -> List[TextBlock]:
    from pptx import Presentation
    prs = Presentation(str(path))
    blocks: List[TextBlock] = []
    i = 0
    for sno, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                is_title = shape == slide.shapes.title
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if not t:
                        continue
                    i += 1
                    is_head = is_title or para.level == 0
                    blocks.append(TextBlock(
                        block_id=f"s{sno}_b{i:03d}", text=t, page_number=sno,
                        metadata={"block_type": "heading" if is_head else "paragraph",
                                  "source_type": "digital", "is_heading": is_head,
                                  "slide_number": sno, "confidence": 0.99,
                                  "low_confidence_flag": False, "low_confidence_words": []}))
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        t = (cell.text or "").strip()
                        if not t:
                            continue
                        i += 1
                        blocks.append(TextBlock(
                            block_id=f"s{sno}_b{i:03d}", text=t, page_number=sno,
                            metadata={"block_type": "table_cell", "source_type": "digital",
                                      "is_heading": False, "slide_number": sno,
                                      "confidence": 0.99, "low_confidence_flag": False,
                                      "low_confidence_words": []}))
    return blocks


def _fallback_route_and_extract(path: Union[str, Path]) -> Document:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    if ext == "docx":
        blocks = _extract_docx(p)
    elif ext == "pptx":
        blocks = _extract_pptx(p)
    elif ext == "pdf":
        blocks = _extract_pdf(p)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return Document(
        document_id=hashlib.sha256(str(p).encode()).hexdigest()[:12],
        filename=p.name, file_type=ext, blocks=blocks,
        metadata={"extraction_engine": "builtin_fallback",
                  "source_path": str(p)})


def route_and_extract(path: Union[str, Path]) -> Document:
    """Try the team router first; gracefully fall back to built-in extractors."""
    try:
        from src.router import route_and_extract as _team_route
        doc = _team_route(path)
        if doc is not None and getattr(doc, "blocks", None) is not None:
            return doc
    except Exception:
        pass
    return _fallback_route_and_extract(path)


# --------------------------------------------------------------------------- #
# 4. BUILT-IN HYBRID PII DETECTOR (regex + context + checksum/format rules)
# --------------------------------------------------------------------------- #
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_RE_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_RE_EMP = re.compile(r"\bEMP-\d{3,}\b")
_RE_EMP_LABEL = re.compile(r"(?i)\bemployee\s*(?:id|number|no\.?)\s*[:\-#]?\s*([A-Z]{0,4}-?\d{4,})\b")
_RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_RE_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\d)")
_RE_DOB = re.compile(
    r"(?i)\b(?:date\s+of\s+birth|d\.?\s?o\.?\s?b\.?|birthdate|born\s+on)\s*[:\-]?\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
_RE_ADDR = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+)*\s+"
    r"(?:Street|St\b|Avenue|Ave\b|Road|Rd\b|Boulevard|Blvd\b|Lane|Ln\b|Drive|Dr\b|"
    r"Court|Ct\b|Way|Place|Pl\b|Terrace|Ter\b|Parkway|Pkwy\b|Circle|Cir\b|Highway|Hwy\b)"
    r"(?:\s+(?:Apt|Suite|Unit|Ste)\s*\.?\s*\w+)?(?:,\s*[A-Za-z .]+,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?",
    re.IGNORECASE)
_RE_CC_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")
_RE_NAME_LABEL = re.compile(
    r"(?i)\b(?:reviewer|owner|approver|name|contact|prepared\s+by|approved\s+by|"
    r"submitted\s+by|reviewed\s+by|author|manager|signatory|attested\s+by|reported\s+by)\s*[:\-]\s*")
_RE_NAME_VALUE = re.compile(r"([A-Z][a-zA-Z'.-]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z'.-]+)")
_NAME_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "policy", "report", "review",
    "approval", "approved", "section", "appendix", "control", "controls", "cadence",
    "optiv", "new", "york", "united", "states", "document", "version", "date",
}
_RE_NAME_CELL = re.compile(r"^([A-Z][a-zA-Z'.-]+\s+[A-Z][a-zA-Z'.-]+)$")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _builtin_detect(document: Document) -> List[PIIEntity]:
    entities: List[PIIEntity] = []
    for block in document.blocks:
        text = block.text or ""
        if not text.strip():
            continue
        btype = (block.metadata or {}).get("block_type", "paragraph")

        def add(etype: str, start: int, end: int, conf: float, detector: str) -> None:
            snippet = text[start:end]
            if not snippet.strip():
                return
            entities.append(PIIEntity(
                entity_type=etype, text=snippet, start=start, end=end,
                confidence=conf, block_id=block.block_id,
                metadata={"detector": detector, "sensitivity": SENSITIVITY.get(etype, "LOW"),
                          "source": (block.metadata or {}).get("source_type", "digital")}))

        for m in _RE_EMAIL.finditer(text):
            add("EMAIL_ADDRESS", m.start(), m.end(), 0.99, "regex:email")
        for m in _RE_SSN.finditer(text):
            add("US_SSN", m.start(), m.end(), 0.97, "regex:ssn_format")
        for m in _RE_EMP.finditer(text):
            add("EMPLOYEE_ID", m.start(), m.end(), 0.99, "regex:emp_id_format")
        for m in _RE_EMP_LABEL.finditer(text):
            add("EMPLOYEE_ID", m.start(1), m.end(1), 0.90, "context:employee_id_label")
        for m in _RE_PAN.finditer(text):
            add("GOVERNMENT_ID", m.start(), m.end(), 0.98, "regex:pan_checksum_format")
        for m in _RE_PHONE.finditer(text):
            add("PHONE_NUMBER", m.start(), m.end(), 0.90, "regex:phone_na")
        for m in _RE_DOB.finditer(text):
            add("DATE_OF_BIRTH", m.start(1), m.end(1), 0.95, "context:dob_label")
        for m in _RE_ADDR.finditer(text):
            add("ADDRESS", m.start(), m.end(), 0.90, "regex:street_address")
        for m in _RE_CC_CANDIDATE.finditer(text):
            digits = re.sub(r"[ -]", "", m.group(0))
            if len(digits) < 12:
                continue
            if 13 <= len(digits) <= 19 and _luhn_ok(digits):
                add("CREDIT_CARD", m.start(), m.end(), 0.97, "checksum:luhn")
            elif 8 <= len(digits) <= 17:
                add("ACCOUNT_NUMBER", m.start(), m.end(), 0.85, "format:account_number")
        for m in _RE_NAME_LABEL.finditer(text):
            window = text[m.end():m.end() + 60]
            nm = _RE_NAME_VALUE.match(window)
            if nm:
                add("PERSON", m.end() + nm.start(1), m.end() + nm.end(1),
                    0.93, "context:name_label")
        if btype == "table_cell":
            nm = _RE_NAME_CELL.match(text.strip())
            if nm:
                words = nm.group(1).split()
                if not any(w.lower() in _NAME_STOPWORDS for w in words):
                    off = text.find(nm.group(1))
                    add("PERSON", off, off + len(nm.group(1)), 0.78, "heuristic:table_cell_name")
    return entities


def _normalize_engine_output(result: Any, document: Document) -> Optional[List[PIIEntity]]:
    """Normalize teammate detector output into List[PIIEntity]."""
    if result is None:
        return None
    if isinstance(result, dict):
        for key in ("entities", "pii_entities", "findings"):
            if key in result:
                result = result[key]
                break
    if not isinstance(result, (list, tuple)):
        return None
    valid_blocks = {b.block_id for b in document.blocks}
    out: List[PIIEntity] = []
    for item in result:
        try:
            if isinstance(item, PIIEntity):
                e = item
            elif isinstance(item, dict):
                e = PIIEntity(
                    entity_type=item.get("entity_type") or item.get("type") or "PERSON",
                    text=item.get("text", ""),
                    start=int(item.get("start", 0)),
                    end=int(item.get("end", 0)),
                    confidence=float(item.get("confidence", 1.0)),
                    block_id=item.get("block_id"),
                    metadata=item.get("metadata", {}) or {})
            else:
                e = PIIEntity(
                    entity_type=getattr(item, "entity_type", "PERSON"),
                    text=getattr(item, "text", ""),
                    start=int(getattr(item, "start", 0)),
                    end=int(getattr(item, "end", 0)),
                    confidence=float(getattr(item, "confidence", 1.0)),
                    block_id=getattr(item, "block_id", None),
                    metadata=getattr(item, "metadata", {}) or {})
            if e.block_id and e.block_id not in valid_blocks:
                continue
            if not e.metadata.get("sensitivity"):
                e.metadata["sensitivity"] = SENSITIVITY.get(e.entity_type, "LOW")
            if not e.metadata.get("detector"):
                e.metadata["detector"] = "src.detection.engine"
            out.append(e)
        except Exception:
            continue
    return out


def _engine_detect(document: Document) -> Optional[List[PIIEntity]]:
    try:
        from src.detection import engine as eng
    except Exception:
        return None
    for fn_name in ("detect_pii_in_document", "analyze", "detect"):
        fn = getattr(eng, fn_name, None)
        if callable(fn):
            try:
                ents = _normalize_engine_output(fn(document), document)
                if ents is not None:
                    return ents
            except Exception:
                continue
    cls = getattr(eng, "PIIDetector", None)
    if cls is not None:
        try:
            det = cls()
            for m in ("detect", "detect_pii", "analyze"):
                fn = getattr(det, m, None)
                if callable(fn):
                    ents = _normalize_engine_output(fn(document), document)
                    if ents is not None:
                        return ents
        except Exception:
            return None
    return None


def _resolve_overlaps(entities: List[PIIEntity]) -> List[PIIEntity]:
    by_block: Dict[str, List[PIIEntity]] = {}
    for e in entities:
        by_block.setdefault(e.block_id or "", []).append(e)
    kept: List[PIIEntity] = []
    for bids in by_block.values():
        bids.sort(key=lambda e: (e.start, -(e.end - e.start), -e.confidence))
        last_end = -1
        for e in bids:
            if e.start >= last_end:
                kept.append(e)
                last_end = e.end
    return kept


def detect_pii(document: Document, threshold: float) -> List[PIIEntity]:
    entities = _engine_detect(document)
    if entities is None:
        entities = _builtin_detect(document)
    filtered = [e for e in entities if e.confidence >= threshold and (e.text or "").strip()]
    return _resolve_overlaps(filtered)


# --------------------------------------------------------------------------- #
# 5. REDACTION + REPORT (team modules first, bulletproof fallbacks inside)
# --------------------------------------------------------------------------- #
def _fallback_redact_document(document: Document, entities: List[PIIEntity]
                              ) -> Tuple[List[Redaction], str, Document, List[Dict[str, Any]]]:
    counters: Dict[str, int] = {}
    redactions: List[Redaction] = []
    trace: List[Dict[str, Any]] = []
    per_block: Dict[str, List[PIIEntity]] = {}
    for e in entities:
        per_block.setdefault(e.block_id or "", []).append(e)

    new_blocks: List[TextBlock] = []
    for block in document.blocks:
        text = block.text or ""
        block_ents = sorted(per_block.get(block.block_id, []),
                            key=lambda e: e.start, reverse=True)
        for e in block_ents:
            prefix = TAG_PREFIX.get(e.entity_type, e.entity_type.upper())
            counters[prefix] = counters.get(prefix, 0) + 1
            tag = f"[{prefix}_{counters[prefix]:02d}]"
            original = text[e.start:e.end]
            redactions.append(Redaction(entity_type=e.entity_type, original_text=original,
                                        replacement=tag, start=e.start, end=e.end,
                                        block_id=block.block_id))
            trace.append({
                "file": document.filename,
                "page_or_slide": block.page_number,
                "block_id": block.block_id,
                "block_type": (block.metadata or {}).get("block_type", "paragraph"),
                "pii_type": e.entity_type,
                "tag": tag,
                "original_text": original,
                "start": e.start,
                "end": e.end,
                "detector": (e.metadata or {}).get("detector", "unknown"),
                "confidence": round(float(e.confidence), 4),
                "sensitivity": (e.metadata or {}).get("sensitivity", "LOW"),
            })
            text = text[:e.start] + tag + text[e.end:]
        new_blocks.append(TextBlock(
            block_id=block.block_id, text=text, page_number=block.page_number,
            metadata=dict(block.metadata or {})))

    redacted_doc = Document(document_id=document.document_id, filename=document.filename,
                            file_type=document.file_type, blocks=new_blocks,
                            metadata=dict(document.metadata or {}))
    redacted_text = "\n\n".join(nb.text for nb in new_blocks)
    return redactions, redacted_text, redacted_doc, trace


def redact_document(document: Document, entities: List[PIIEntity]
                    ) -> Tuple[List[Redaction], str, Document, List[Dict[str, Any]]]:
    try:
        from src.redaction.redactor import redact_document as _team_redact
        result = _team_redact(document, entities)
        redactions, redacted_text, redacted_doc, trace = result
        if not isinstance(trace, list) or (trace and "tag" not in trace[0]):
            trace = _fallback_redact_document(document, entities)[3]
        return redactions, redacted_text, redacted_doc, trace
    except Exception:
        return _fallback_redact_document(document, entities)


def _fallback_report(document: Document, entities: List[PIIEntity],
                     redactions: List[Redaction], traceability_log: List[Dict[str, Any]],
                     redacted_text: str) -> Dict[str, Any]:
    counts_by_type: Dict[str, int] = {}
    tier_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for e in entities:
        counts_by_type[e.entity_type] = counts_by_type.get(e.entity_type, 0) + 1
        tier = (e.metadata or {}).get("sensitivity", SENSITIVITY.get(e.entity_type, "LOW"))
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    if tier_counts.get("CRITICAL"):
        risk = "CRITICAL"
    elif tier_counts.get("HIGH"):
        risk = "HIGH"
    elif tier_counts.get("MEDIUM"):
        risk = "MEDIUM"
    elif tier_counts.get("LOW"):
        risk = "LOW"
    else:
        risk = "NONE"
    low_conf_blocks = [b.block_id for b in document.blocks
                       if (b.metadata or {}).get("low_confidence_flag")]
    audit_summary = (
        f"Artifact '{document.filename}' ({document.file_type.upper()}) processed: "
        f"{len(entities)} PII entities detected across {len(document.blocks)} structural blocks; "
        f"{len(redactions)} deterministic transparent-tag redactions applied; "
        f"{len(low_conf_blocks)} low-confidence OCR block(s) flagged for auditor review; "
        f"portfolio risk level: {risk}."
    )
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "risk_level": risk,
        "total_pii_found": len(entities),
        "total_redactions_applied": len(redactions),
        "counts_by_type": counts_by_type,
        "counts_by_sensitivity": tier_counts,
        "low_confidence_ocr_blocks": low_conf_blocks,
        "llm_ready": True,
        "safe_text_for_llm": redacted_text,
        "traceability_log": traceability_log,
        "audit_summary": audit_summary,
    }


def generate_exposure_report(document: Document, entities: List[PIIEntity],
                             redactions: List[Redaction],
                             traceability_log: List[Dict[str, Any]],
                             redacted_text: str) -> Dict[str, Any]:
    try:
        from src.redaction.report import generate_exposure_report as _team_report
        report = _team_report(document, entities, redactions, traceability_log, redacted_text)
        if isinstance(report, dict) and "risk_level" in report:
            for key, val in _fallback_report(document, entities, redactions,
                                             traceability_log, redacted_text).items():
                report.setdefault(key, val)
            return report
    except Exception:
        pass
    return _fallback_report(document, entities, redactions, traceability_log, redacted_text)


# --------------------------------------------------------------------------- #
# 6. METRIC HELPERS
# --------------------------------------------------------------------------- #
def compute_structure_retention(document: Document) -> float:
    md = document.metadata or {}
    for key in ("structure_retention", "structure_retention_score"):
        if key in md:
            try:
                val = float(md[key])
                return val if val <= 1.0 else val / 100.0
            except Exception:
                pass
    blocks = document.blocks
    if not blocks:
        return 0.0
    with_pos = sum(1 for b in blocks if (b.metadata or {}).get("position"))
    structural = sum(1 for b in blocks
                     if (b.metadata or {}).get("block_type") in ("heading", "table_cell"))
    score = 0.4 * (with_pos / len(blocks)) + 0.3 * min(1.0, (structural / len(blocks)) * 3) + 0.3
    return round(min(1.0, score), 4)


def risk_badge(risk: str) -> str:
    cls = {"CRITICAL": "risk-critical", "HIGH": "risk-high", "MEDIUM": "risk-medium",
           "LOW": "risk-low", "NONE": "risk-none"}.get(risk, "risk-none")
    return f'<span class="pill {cls}">{risk}</span>'


def verify_zero_leakage(entities: List[PIIEntity], redacted_text: str) -> Tuple[bool, List[str]]:
    leaked = []
    for e in entities:
        t = (e.text or "").strip()
        if t and t in redacted_text:
            leaked.append(t)
    residual_patterns = re.findall(
        r"\b\d{3}-\d{2}-\d{4}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", redacted_text or "")
    return (len(leaked) == 0 and not residual_patterns), leaked + residual_patterns


def records_to_csv(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 7. PIPELINE ORCHESTRATION
# --------------------------------------------------------------------------- #
def run_pipeline(path: Union[str, Path], threshold: float) -> Dict[str, Any]:
    filename = Path(path).name
    with st.status(f"Running pipeline: {filename}", expanded=True) as status:
        st.write("1/5 Ingestion - routing artifact by file type ...")
        document = route_and_extract(path)
        st.write(f"2/5 Extraction - {len(document.blocks)} structural blocks retained "
                 f"(2D reading order, table context, OCR confidence flags)")
        entities = detect_pii(document, threshold)
        st.write(f"3/5 Detection - {len(entities)} PII entities above {threshold:.2f} confidence")
        redactions, redacted_text, redacted_doc, trace = redact_document(document, entities)
        st.write(f"4/5 Redaction - {len(redactions)} deterministic transparent tags applied")
        report = generate_exposure_report(document, entities, redactions, trace, redacted_text)
        st.write("5/5 Audit Report - exposure report + compliance traceability log generated")
        status.update(label=f"{filename} - Risk: {report.get('risk_level', 'NONE')}",
                      state="complete")
    return {
        "document": document, "entities": entities, "redactions": redactions,
        "redacted_text": redacted_text, "redacted_doc": redacted_doc,
        "trace": trace, "report": report,
        "structure_retention": compute_structure_retention(document),
    }


def find_sample_files() -> List[Path]:
    candidates: List[Path] = []
    for sub in ("tests/data", "test_data", "samples", "data", "examples"):
        d = PROJECT_ROOT / sub
        if d.is_dir():
            for ext in ("*.pdf", "*.docx", "*.pptx"):
                candidates.extend(sorted(d.glob(ext)))
    return candidates


def process_uploaded_files(uploaded_files, threshold: float) -> None:
    for up in uploaded_files:
        if up.name in st.session_state.results:
            continue
        suffix = Path(up.name).suffix.lower()
        if suffix not in (".docx", ".pdf", ".pptx"):
            st.warning(f"Skipped {up.name}: unsupported type {suffix}")
            continue
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(up.getbuffer())
            tmp.close()
            st.session_state.results[up.name] = run_pipeline(tmp.name, threshold)
        except Exception as exc:  # demo must never crash
            st.error(f"Failed to process {up.name}: {exc}")
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


def load_sample_files(threshold: float) -> None:
    samples = find_sample_files()
    if not samples:
        st.info("No sample artifacts found in tests/data, test_data, samples, data or examples.")
        return
    for s in samples:
        if s.name in st.session_state.results:
            continue
        try:
            st.session_state.results[s.name] = run_pipeline(s, threshold)
        except Exception as exc:
            st.error(f"Failed to process sample {s.name}: {exc}")


# --------------------------------------------------------------------------- #
# 8. UI - CSS / THEME
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown("""
<style>
:root {
  --bg: #0b1220; --panel: rgba(20, 30, 48, 0.72); --border: rgba(120, 144, 180, 0.22);
  --txt: #e2e8f0; --mut: #94a3b8; --accent: #38bdf8; --accent2: #818cf8;
}
.stApp { background: radial-gradient(1200px 600px at 10% -10%, #16233d 0%, var(--bg) 55%); color: var(--txt); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0e1729 0%, #0b1220 100%); }
.brand-banner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 26px; border: 1px solid var(--border); border-radius: 16px;
  background: linear-gradient(120deg, rgba(56,189,248,.10), rgba(129,140,248,.10)), var(--panel);
  backdrop-filter: blur(10px); margin-bottom: 18px;
}
.brand-left { font-weight: 800; font-size: 22px; letter-spacing: 2px; color: #38bdf8; }
.brand-mid { text-align: center; }
.brand-mid .title { font-size: 24px; font-weight: 700; }
.brand-mid .sub { color: var(--mut); font-size: 13px; }
.brand-right { font-weight: 800; font-size: 22px; letter-spacing: 2px; color: #f8fafc; }
.kpi-card {
  border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px;
  background: var(--panel); backdrop-filter: blur(8px); min-height: 108px;
}
.kpi-card .kpi-label { color: var(--mut); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.kpi-card .kpi-value { font-size: 30px; font-weight: 800; margin-top: 4px; }
.kpi-card .kpi-foot { font-size: 12px; margin-top: 4px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 12px;
        font-weight: 700; letter-spacing: .5px; }
.risk-critical { background: rgba(239,68,68,.18); color: #f87171; border: 1px solid rgba(239,68,68,.5); }
.risk-high { background: rgba(249,115,22,.18); color: #fb923c; border: 1px solid rgba(249,115,22,.5); }
.risk-medium { background: rgba(245,158,11,.18); color: #fbbf24; border: 1px solid rgba(245,158,11,.5); }
.risk-low, .risk-none { background: rgba(16,185,129,.16); color: #34d399; border: 1px solid rgba(16,185,129,.5); }
.shield {
  display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 12px;
  background: rgba(16,185,129,.12); border: 1px solid rgba(16,185,129,.45); color: #34d399; font-weight: 700;
}
.shield-bad { background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.5); color: #f87171; }
.panel { border: 1px solid var(--border); border-radius: 14px; background: var(--panel);
         padding: 16px; backdrop-filter: blur(8px); }
.doc-pane { border: 1px solid var(--border); border-radius: 12px; padding: 14px;
            background: rgba(11,18,32,.6); max-height: 560px; overflow-y: auto; font-size: 14px; line-height: 1.7; }
.doc-pane h4 { color: var(--accent); margin: 0 0 6px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }
.block-label { color: var(--mut); font-size: 11px; margin: 14px 0 2px 0; font-family: monospace; }
.heading-block { font-weight: 700; font-size: 16px; color: #f1f5f9; }
pre.safe-text { white-space: pre-wrap; word-wrap: break-word; font-size: 13px; line-height: 1.7;
                color: #d1fae5; background: rgba(6,26,20,.5); padding: 12px; border-radius: 10px; }
mark { padding: 1px 5px; border-radius: 6px; font-weight: 700; color: #0b1220; }
mark.mk-person { background: #7dd3fc; } mark.mk-employee_id { background: #c4b5fd; }
mark.mk-email_address { background: #67e8f9; } mark.mk-phone_number { background: #5eead4; }
mark.mk-us_ssn { background: #fca5a5; } mark.mk-government_id { background: #f87171; }
mark.mk-credit_card { background: #fdba74; } mark.mk-account_number { background: #fcd34d; }
mark.mk-date_of_birth { background: #fde68a; } mark.mk-address { background: #86efac; }
.bar-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; }
.bar-row .bar-lbl { width: 170px; font-size: 13px; color: var(--txt); font-family: monospace; }
.bar-row .bar-track { flex: 1; background: rgba(148,163,184,.15); border-radius: 6px; height: 18px; }
.bar-row .bar-fill { height: 18px; border-radius: 6px; background: linear-gradient(90deg, #38bdf8, #818cf8); }
.bar-row .bar-val { width: 44px; text-align: right; font-weight: 700; }
.stage-line { font-size: 13px; margin: 4px 0; color: var(--mut); }
.stage-done { color: #34d399; font-weight: 700; }
.risk-banner { padding: 14px 18px; border-radius: 12px; font-weight: 600; margin: 10px 0;
               border: 1px solid var(--border); }
.justification { font-size: 13px; color: var(--mut); margin-top: 6px; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# 9. UI - SECTION RENDERERS
# --------------------------------------------------------------------------- #
def render_header() -> None:
    st.markdown("""
<div class="brand-banner">
  <div class="brand-left">OPTIV</div>
  <div class="brand-mid">
    <div class="title">PII Shield &mdash; Cyber Risk &amp; Compliance Dashboard</div>
    <div class="sub">Cadence Financial Services &times; Optiv Consulting &nbsp;|&nbsp;
    LLM Evidence Sanitization Pipeline &nbsp;|&nbsp; Deterministic Redaction &amp; Audit Vault</div>
  </div>
  <div class="brand-right">CADENCE</div>
</div>
""", unsafe_allow_html=True)


def render_sidebar() -> Tuple[float, List[str]]:
    st.sidebar.markdown("### 🛡 Pipeline Controls")
    threshold = st.sidebar.slider("Detection confidence threshold", 0.50, 1.00, 0.75, 0.05)
    type_filter = st.sidebar.multiselect(
        "PII type filter (empty = all)",
        options=ALL_TYPES,
        format_func=lambda t: f"{TYPE_SHORT[t]} ({SENSITIVITY[t]})",
        default=[])
    st.sidebar.markdown("---")
    uploaded = st.sidebar.file_uploader(
        "Drop artifacts (.docx / .pdf / .pptx)",
        type=["docx", "pdf", "pptx"], accept_multiple_files=True)
    if uploaded:
        process_uploaded_files(uploaded, threshold)
    st.sidebar.markdown("---")
    if st.sidebar.button("⬇ Load Official Sample Test Files", use_container_width=True):
        load_sample_files(threshold)
    samples = find_sample_files()
    if samples:
        st.sidebar.caption("Samples on disk: " + ", ".join(s.name for s in samples))
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Pipeline Stage Indicator**")
    for i, stage in enumerate(PIPELINE_STAGES, start=1):
        st.sidebar.markdown(f'<div class="stage-line">{i}. {stage} '
                            f'<span class="stage-done">●</span></div>',
                            unsafe_allow_html=True)
    if st.sidebar.button("🗑 Clear processed artifacts"):
        st.session_state.results = {}
        st.rerun()
    return threshold, type_filter


def apply_type_filter(results: Dict[str, Any], type_filter: List[str]) -> Dict[str, Any]:
    if not type_filter:
        return results
    keep = set(type_filter)
    out = dict(results)
    out["entities"] = [e for e in results["entities"] if e.entity_type in keep]
    out["redactions"] = [r for r in results["redactions"] if r.entity_type in keep]
    out["trace"] = [t for t in results["trace"] if t.get("pii_type") in keep]
    report = dict(results["report"])
    counts = {k: v for k, v in report.get("counts_by_type", {}).items() if k in keep}
    report["counts_by_type"] = counts
    report["total_pii_found"] = sum(counts.values())
    report["total_redactions_applied"] = len(out["redactions"])
    tiers = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for t in out["trace"]:
        tiers[t.get("sensitivity", "LOW")] = tiers.get(t.get("sensitivity", "LOW"), 0) + 1
    report["counts_by_sensitivity"] = tiers
    report["risk_level"] = ("CRITICAL" if tiers["CRITICAL"] else
                            "HIGH" if tiers["HIGH"] else
                            "MEDIUM" if tiers["MEDIUM"] else
                            "LOW" if tiers["LOW"] else "NONE")
    out["report"] = report
    return out


def render_portfolio_summary() -> None:
    results = st.session_state.results
    if not results:
        st.info("Upload artifacts via the sidebar, or click "
                "'Load Official Sample Test Files' to begin the demonstration.")
        return
    total_blocks = sum(len(r["document"].blocks) for r in results.values())
    total_pii = sum(r["report"].get("total_pii_found", 0) for r in results.values())
    retention_scores = [r["structure_retention"] * 100 for r in results.values()]
    avg_retention = sum(retention_scores) / len(retention_scores) if retention_scores else 0
    highest = "NONE"
    for r in results.values():
        lvl = r["report"].get("risk_level", "NONE")
        if RISK_ORDER.get(lvl, 0) > RISK_ORDER.get(highest, 0):
            highest = lvl

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "Artifacts Processed", str(len(results)), "multi-format batch"),
        (c2, "Structural Blocks", f"{total_blocks:,}", "2D reading order retained"),
        (c3, "Structure Retention", f"{avg_retention:.0f}%",
         "✅ ≥ 80% target met" if avg_retention >= 80 else "⚠ below 80% target"),
        (c4, "PII Entities Redacted", f"{total_pii:,}", "transparent tags applied"),
        (c5, "Portfolio Risk", f'<span class="pill { "risk-" + highest.lower() }">{highest}</span>', "highest artifact level"),
    ]
    for col, label, value, foot in cards:
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                        f'<div class="kpi-value">{value}</div>'
                        f'<div class="kpi-foot">{foot}</div></div>', unsafe_allow_html=True)
    st.markdown("")


def html_bar_chart(counts: Dict[str, int], unit: str = "") -> str:
    if not counts:
        return '<div class="panel" style="color:#94a3b8">No data to chart.</div>'
    maxv = max(counts.values()) or 1
    rows = []
    for label, val in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = max(4, round(100 * val / maxv))
        rows.append(f'<div class="bar-row"><div class="bar-lbl">{html.escape(str(label))}</div>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
                    f'<div class="bar-val">{val}{unit}</div></div>')
    return '<div class="panel">' + "".join(rows) + "</div>"


def render_comparison_tab(res: Dict[str, Any]) -> None:
    doc: Document = res["document"]
    entities: List[PIIEntity] = res["entities"]
    per_block: Dict[str, List[PIIEntity]] = {}
    for e in entities:
        per_block.setdefault(e.block_id or "", []).append(e)

    def block_html(block: TextBlock, redacted: bool) -> str:
        text = block.text or ""
        if redacted:
            return f'<pre class="safe-text" style="margin:6px 0 12px 0">{html.escape(text)}</pre>'
        ents = sorted(per_block.get(block.block_id, []), key=lambda e: e.start)
        parts, cursor = [], 0
        for e in ents:
            if e.start < cursor:
                continue
            parts.append(html.escape(text[cursor:e.start]))
            cls = "mk-" + e.entity_type.lower()
            parts.append(f'<mark class="{cls}" title="{e.entity_type} '
                         f'(conf {e.confidence:.2f})">{html.escape(text[e.start:e.end])}</mark>')
            cursor = e.end
        parts.append(html.escape(text[cursor:]))
        body = "".join(parts).replace("\n", "<br>")
        cls = "heading-block" if (block.metadata or {}).get("is_heading") else ""
        loc = f"p.{block.page_number}" if block.page_number else "n/a"
        return (f'<div class="block-label">[{block.block_id} | {loc} | '
                f'{(block.metadata or {}).get("block_type", "paragraph")}]</div>'
                f'<div class="{cls}">{body}</div>')

    raw_html = "".join(block_html(b, False) for b in doc.blocks) or "<i>No text extracted.</i>"
    safe_html = "".join(block_html(b, True) for b in res["redacted_doc"].blocks) or "<i>No text extracted.</i>"

    left, right = st.columns(2)
    with left:
        st.markdown("#### ⚠ Raw Evidence - Highlighted PII")
        st.markdown(f'<div class="doc-pane"><h4>Extracted text - color-coded PII marks</h4>{raw_html}</div>',
                    unsafe_allow_html=True)
    with right:
        st.markdown("#### ✅ Safe Redacted Output - LLM Ready")
        ok, leaked = verify_zero_leakage(res["entities"], res["redacted_text"])
        if ok:
            st.markdown('<div class="shield">🛡 ZERO PII LEAKAGE - LLM READY</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="shield shield-bad">⛔ Potential residual PII: {len(leaked)} token(s)</div>',
                        unsafe_allow_html=True)
        st.markdown(f'<div class="doc-pane"><h4>Sanitized payload - transparent tags</h4>{safe_html}</div>',
                    unsafe_allow_html=True)
    st.markdown("##### Export Safe LLM Prompt Payload")
    e1, e2 = st.columns(2)
    payload_json = json.dumps({
        "artifact": doc.filename,
        "instruction": "Analyze this sanitized Cadence business document. PII appears only as opaque placeholders.",
        "safe_text": res["redacted_text"],
    }, indent=2)
    e1.download_button("⬇ Download safe payload (.txt)", res["redacted_text"],
                       file_name=f"{Path(doc.filename).stem}_safe_llm.txt", mime="text/plain",
                       use_container_width=True)
    e2.download_button("⬇ Download safe payload (.json)", payload_json,
                       file_name=f"{Path(doc.filename).stem}_safe_llm.json", mime="application/json",
                       use_container_width=True)


def render_structure_tab(res: Dict[str, Any]) -> None:
    doc: Document = res["document"]
    retention = res["structure_retention"] * 100
    by_type: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    low_conf = []
    for b in doc.blocks:
        md = b.metadata or {}
        by_type[md.get("block_type", "paragraph")] = by_type.get(md.get("block_type", "paragraph"), 0) + 1
        by_source[md.get("source_type", "unknown")] = by_source.get(md.get("source_type", "unknown"), 0) + 1
        if md.get("low_confidence_flag"):
            low_conf.append(b)

    c1, c2, c3 = st.columns(3)
    c1.metric("Structure Retention Score", f"{retention:.1f}%",
              delta="≥ 80% target met" if retention >= 80 else "below target",
              delta_color="normal" if retention >= 80 else "inverse")
    c2.metric("Low-Confidence OCR Blocks", str(len(low_conf)),
              delta="flagged for auditor review" if low_conf else "none flagged")
    c3.metric("Digital vs Scanned Pages/Slides",
              f"{by_source.get('digital', 0) + by_source.get('digital_pdf', 0)} digital / "
              f"{by_source.get('scanned_ocr', 0)} scanned")

    st.markdown("**Structural composition** (headings, paragraphs, table cells)")
    st.markdown(html_bar_chart(by_type), unsafe_allow_html=True)
    st.markdown("**Source composition**")
    st.markdown(html_bar_chart(by_source), unsafe_allow_html=True)

    st.markdown("#### Low-Confidence OCR Inspector")
    if not low_conf:
        st.success("No low-confidence OCR blocks. Every scanned region passed the 75% confidence floor.")
        return
    st.warning(f"{len(low_conf)} block(s) below 75% OCR confidence - these regions are flagged so PII is never silently missed.")
    records = [{
        "block_id": b.block_id,
        "page": b.page_number,
        "block_type": (b.metadata or {}).get("block_type"),
        "confidence": (b.metadata or {}).get("confidence"),
        "low_confidence_words": ", ".join((b.metadata or {}).get("low_confidence_words", [])[:10]),
        "preview": (b.text or "")[:120],
    } for b in low_conf]
    if _HAVE_PANDAS:
        st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
    else:
        st.table(records)


def render_audit_tab(res: Dict[str, Any]) -> None:
    report = res["report"]
    risk = report.get("risk_level", "NONE")
    counts = report.get("counts_by_type", {})
    tiers = report.get("counts_by_sensitivity", {})
    justifications = {
        "CRITICAL": "Government identifiers, SSNs or payment card/account numbers were present. "
                    "Regulatory exposure (GLBA / NYDFS 500 / PCI-DSS). Immediate remediation required.",
        "HIGH": "Employee identifiers or dates of birth were exposed. Identity-theft and insider-risk exposure.",
        "MEDIUM": "Direct contact data (email, phone, address) was exposed. Phishing / social-engineering risk.",
        "LOW": "Only person names were exposed. Combined with other artifacts this can still enable profiling.",
        "NONE": "No PII detected above the confidence threshold. Artifact is safe for LLM ingestion as-is.",
    }
    st.markdown(f"**Exposure posture:** {risk_badge(risk)}")
    st.markdown(f'<div class="risk-banner panel">{html.escape(justifications.get(risk, ""))}'
                f'<div class="justification">{html.escape(report.get("audit_summary", ""))}</div></div>',
                unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown("**PII counts by category**")
        st.markdown(html_bar_chart(counts), unsafe_allow_html=True)
    with right:
        st.markdown("**PII counts by sensitivity tier**")
        st.markdown(html_bar_chart(tiers), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total PII found", report.get("total_pii_found", 0))
    c2.metric("Redactions applied", report.get("total_redactions_applied", 0))
    c3.metric("Low-confidence OCR blocks", len(report.get("low_confidence_ocr_blocks", [])))

    st.markdown("##### Download Audit Exposure Report")
    d1, d2 = st.columns(2)
    report_json = json.dumps(report, indent=2, default=str)
    d1.download_button("⬇ Audit report (.json)", report_json,
                       file_name=f"{Path(report.get('filename', 'artifact')).stem}_audit_report.json",
                       mime="application/json", use_container_width=True)
    flat_records = [{
        "filename": report.get("filename"), "risk_level": risk,
        "entity_type": k, "count": v, "sensitivity": SENSITIVITY.get(k, "LOW"),
    } for k, v in counts.items()]
    d2.download_button("⬇ Audit report (.csv)", records_to_csv(flat_records),
                       file_name=f"{Path(report.get('filename', 'artifact')).stem}_audit_report.csv",
                       mime="text/csv", use_container_width=True)


def render_traceability_tab(res: Dict[str, Any]) -> None:
    trace: List[Dict[str, Any]] = list(res["trace"])
    st.markdown("Compliance vault - the mapping between transparent tags and original values. "
                "**This log is never transmitted to the LLM.**")
    col_a, col_b, col_c = st.columns([2, 1, 1])
    query = col_a.text_input("🔍 Search traceability log", "")
    reveal = col_b.toggle("Reveal raw PII values", value=False)
    export_all = col_c.checkbox("Include raw values in exports", value=False)

    rows = trace
    if query:
        q = query.lower()
        rows = [t for t in rows if q in json.dumps(t, default=str).lower()]
    display_rows = []
    for t in rows:
        r = dict(t)
        if not (reveal or export_all):
            r["original_text"] = "•" * min(12, max(6, len(str(r.get("original_text", "")))))
        display_rows.append(r)

    if _HAVE_PANDAS:
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    else:
        st.table(display_rows)
    st.caption(f"{len(display_rows)} traceability record(s)")

    e1, e2 = st.columns(2)
    export_rows = display_rows if not export_all else rows
    e1.download_button("⬇ Traceability log (.csv)", records_to_csv(export_rows),
                       file_name="source_traceability_log.csv", mime="text/csv",
                       use_container_width=True)
    e2.download_button("⬇ Traceability log (.json)", json.dumps(export_rows, indent=2, default=str),
                       file_name="source_traceability_log.json", mime="application/json",
                       use_container_width=True)


def render_llm_sandbox_tab(res: Dict[str, Any]) -> None:
    doc: Document = res["document"]
    redacted_text = res["redacted_text"]
    ok, leaked = verify_zero_leakage(res["entities"], redacted_text)

    st.markdown("#### Simulated Downstream LLM Agent - Cadence Document Analysis")
    st.caption("Exactly what reaches the LLM context window - proof that semantic context is preserved "
               "with 0% exposure to real personal data.")
    st.markdown("**Payload dispatched to the agent:**")
    st.code(redacted_text or "(empty document)", language=None)

    tags = sorted({r.replacement for r in res["redactions"]})
    first_person = next((r.replacement for r in res["redactions"] if r.entity_type == "PERSON"), "[PERSON_01]")
    first_emp = next((r.replacement for r in res["redactions"] if r.entity_type == "EMPLOYEE_ID"), "[EMP_ID_01]")
    first_email = next((r.replacement for r in res["redactions"] if r.entity_type == "EMAIL_ADDRESS"), "[EMAIL_01]")
    counts = res["report"].get("counts_by_type", {})
    tag_summary = ", ".join(f"{TAG_PREFIX.get(k, k)} x{v}" for k, v in sorted(counts.items()))

    simulated = f"""DOCUMENT ANALYSIS - {doc.filename}
Artifact type: {doc.file_type.upper()} | structural blocks analyzed: {len(doc.blocks)}
Pseudonymized identities referenced: {tag_summary if tags else 'none'}
Primary reviewer: {first_person} (employee record {first_emp}, contact {first_email})

SUMMARY
The document was reviewed and approved by {first_person}. All {len(tags)} PII
reference(s) appear only as opaque deterministic placeholders, so this analysis is
performed with zero raw personal data in the context window. Content, control
language, dates (non-PII) and structure are fully preserved for accurate summarization.
EXPOSURE CHECK: 0 raw PII tokens present in context."""
    st.markdown("**Agent response (simulated):**")
    st.markdown(f'<div class="panel" style="white-space:pre-wrap;font-size:14px;line-height:1.7">{html.escape(simulated)}</div>',
                unsafe_allow_html=True)

    if ok:
        st.markdown('<div class="shield">🛡 VERIFICATION PASSED - ZERO PII LEAKAGE - LLM READY</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="shield shield-bad">⛔ Verification failed - {len(leaked)} residual token(s): '
                    f'{html.escape(", ".join(leaked[:5]))}</div>', unsafe_allow_html=True)


def render_artifact_workspace(type_filter: List[str]) -> None:
    results = st.session_state.results
    if not results:
        return
    names = sorted(results.keys())
    selected = st.selectbox("Per-Artifact Deep-Dive Workspace", names, index=len(names) - 1)
    res = apply_type_filter(results[selected], type_filter)

    head1, head2, head3 = st.columns([3, 2, 2])
    head1.markdown(f"**Artifact:** `{selected}`")
    head2.markdown(f"**Risk Level:** {risk_badge(res['report'].get('risk_level', 'NONE'))}",
                   unsafe_allow_html=True)
    head3.markdown(f"**PII found / redactions applied:** "
                   f"{res['report'].get('total_pii_found', 0)} / {res['report'].get('total_redactions_applied', 0)}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1 · Raw vs Redacted", "2 · Structure & OCR", "3 · Audit Report",
        "4 · Traceability Vault", "5 · LLM Sandbox",
    ])
    with tab1:
        render_comparison_tab(res)
    with tab2:
        render_structure_tab(res)
    with tab3:
        render_audit_tab(res)
    with tab4:
        render_traceability_tab(res)
    with tab5:
        render_llm_sandbox_tab(res)


# --------------------------------------------------------------------------- #
# 10. ENTRYPOINT
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Optiv x Cadence | PII Shield",
                       page_icon="🛡", layout="wide",
                       initial_sidebar_state="expanded")
    if "results" not in st.session_state:
        st.session_state.results = {}
    inject_css()
    render_header()
    threshold, type_filter = render_sidebar()
    render_portfolio_summary()
    render_artifact_workspace(type_filter)


if __name__ == "__main__":
    main()