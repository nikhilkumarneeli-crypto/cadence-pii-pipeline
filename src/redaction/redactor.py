"""PII Redaction and Transparent Tagging module (Member 5).

Replaces detected PII entities with deterministic, sequential transparent tags
(e.g., [EMAIL_01], [PERSON_02]) so downstream LLMs retain context without seeing
raw personal data. Also builds a separate source traceability log for internal audit.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple, Union

from src.common.schema import Document, PIIEntity, PIIFinding, Redaction

TAG_PREFIX_MAP: Dict[str, str] = {
    "EMAIL_ADDRESS": "EMAIL",
    "EMAIL": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "PHONE": "PHONE",
    "PERSON": "PERSON",
    "FULL_NAME": "PERSON",
    "NAME": "PERSON",
    "EMPLOYEE_ID": "EMP_ID",
    "EMP_ID": "EMP_ID",
    "US_SSN": "SSN",
    "SSN": "SSN",
    "GOVERNMENT_ID": "GOV_ID",
    "GOV_ID": "GOV_ID",
    "PAN": "GOV_ID",
    "CREDIT_CARD": "ACCOUNT",
    "ACCOUNT_NUMBER": "ACCOUNT",
    "DATE_OF_BIRTH": "DOB",
    "DOB": "DOB",
    "ADDRESS": "ADDRESS",
    "LOCATION": "ADDRESS",
}


def _normalize_tag_prefix(entity_type: str) -> str:
    clean = (entity_type or "PII").strip().upper().replace(" ", "_")
    return TAG_PREFIX_MAP.get(clean, clean)


class PIIRedactor:
    """Redacts PII entities in raw text or Document objects using transparent sequential tags."""

    def __init__(self, tag_format: str = "[{prefix}_{index:02d}]") -> None:
        self.tag_format = tag_format
        self.last_traceability_log: List[Dict[str, Any]] = []
        self.last_redacted_document: Optional[Document] = None

    def redact_text(
        self,
        text: str,
        entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
        block_id: Optional[str] = None,
    ) -> Tuple[List[Redaction], str]:
        """Redacts a single text string and returns (redactions, redacted_text)."""
        if not text or not entities:
            return [], text

        normalized: List[Dict[str, Any]] = []
        for e in entities:
            if isinstance(e, dict):
                e_type = e.get("entity_type", "PII")
                e_text = e.get("text", "")
                start = int(e.get("start", -1))
                end = int(e.get("end", -1))
                b_id = e.get("block_id", block_id)
            else:
                e_type = getattr(e, "entity_type", "PII")
                e_text = getattr(e, "text", "")
                start = int(getattr(e, "start", -1))
                end = int(getattr(e, "end", -1))
                b_id = getattr(e, "block_id", block_id)

            if 0 <= start < end <= len(text) and (not e_text or text[start:end] == e_text):
                s_idx, e_idx = start, end
            elif e_text and e_text in text:
                s_idx = text.index(e_text)
                e_idx = s_idx + len(e_text)
            else:
                continue

            normalized.append({
                "entity_type": e_type,
                "text": text[s_idx:e_idx],
                "start": s_idx,
                "end": e_idx,
                "block_id": b_id,
            })

        normalized.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
        non_overlapping: List[Dict[str, Any]] = []
        last_end = -1
        for item in normalized:
            if item["start"] >= last_end:
                non_overlapping.append(item)
                last_end = item["end"]

        counters: Dict[str, int] = defaultdict(int)
        value_to_tag: Dict[Tuple[str, str], str] = {}
        redactions: List[Redaction] = []

        for item in non_overlapping:
            prefix = _normalize_tag_prefix(item["entity_type"])
            cache_key = (prefix, item["text"].strip().lower())
            if cache_key not in value_to_tag:
                counters[prefix] += 1
                value_to_tag[cache_key] = self.tag_format.format(
                    prefix=prefix, index=counters[prefix]
                )
            tag = value_to_tag[cache_key]
            redactions.append(
                Redaction(
                    entity_type=item["entity_type"],
                    original_text=item["text"],
                    replacement=tag,
                    start=item["start"],
                    end=item["end"],
                    block_id=item["block_id"],
                )
            )

        redacted_str = text
        for r in reversed(redactions):
            redacted_str = redacted_str[: r.start] + r.replacement + redacted_str[r.end :]

        return redactions, redacted_str

    def redact(
        self,
        document: Union[Document, str],
        entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
    ) -> Tuple[List[Redaction], str]:
        """Primary entry point invoked by Member 1's PIIPipeline._run_redaction.

        Returns:
            Tuple of (redactions: List[Redaction], redacted_text: str).
            Also stores `self.last_traceability_log` and `self.last_redacted_document`.
        """
        if isinstance(document, str):
            return self.redact_text(document, entities)

        redactions, redacted_text, redacted_doc, trace_log = self.redact_document(document, entities)
        self.last_redacted_document = redacted_doc
        self.last_traceability_log = trace_log
        return redactions, redacted_text

    def redact_document(
        self,
        document: Document,
        entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
    ) -> Tuple[List[Redaction], str, Document, List[Dict[str, Any]]]:
        """Redacts all blocks in a Document and builds a separate audit traceability log.

        Returns:
            Tuple of (redactions, redacted_text, redacted_document, traceability_log).
        """
        redacted_doc = deepcopy(document)
        all_redactions: List[Redaction] = []
        traceability_log: List[Dict[str, Any]] = []

        counters: Dict[str, int] = defaultdict(int)
        value_to_tag: Dict[Tuple[str, str], str] = {}

        by_block: Dict[Optional[str], List[Any]] = defaultdict(list)
        for e in entities:
            b_id = e.get("block_id") if isinstance(e, dict) else getattr(e, "block_id", None)
            by_block[b_id].append(e)

        for block in redacted_doc.blocks:
            block_entities = list(by_block.get(block.block_id, []))
            for unlinked in by_block.get(None, []):
                u_text = unlinked.get("text", "") if isinstance(unlinked, dict) else getattr(unlinked, "text", "")
                if u_text and u_text in block.text:
                    block_entities.append(unlinked)

            if not block_entities:
                continue

            spans: List[Dict[str, Any]] = []
            for e in block_entities:
                e_type = e.get("entity_type", "PII") if isinstance(e, dict) else getattr(e, "entity_type", "PII")
                e_text = e.get("text", "") if isinstance(e, dict) else getattr(e, "text", "")
                start = int(e.get("start", -1) if isinstance(e, dict) else getattr(e, "start", -1))
                end = int(e.get("end", -1) if isinstance(e, dict) else getattr(e, "end", -1))
                conf = float(e.get("confidence", 1.0) if isinstance(e, dict) else getattr(e, "confidence", 1.0))
                meta = (e.get("metadata", {}) if isinstance(e, dict) else getattr(e, "metadata", {})) or {}
                detector = (
                    e.get("detector") if isinstance(e, dict) else getattr(e, "detector", None)
                ) or meta.get("detector", "presidio+regex")

                if 0 <= start < end <= len(block.text) and (not e_text or block.text[start:end] == e_text):
                    s_idx, e_idx = start, end
                elif e_text and e_text in block.text:
                    s_idx = block.text.index(e_text)
                    e_idx = s_idx + len(e_text)
                else:
                    continue

                spans.append({
                    "entity_type": e_type,
                    "original_text": block.text[s_idx:e_idx],
                    "start": s_idx,
                    "end": e_idx,
                    "confidence": conf,
                    "detector": detector,
                })

            spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
            clean_spans: List[Dict[str, Any]] = []
            last_end = -1
            for s in spans:
                if s["start"] >= last_end:
                    clean_spans.append(s)
                    last_end = s["end"]

            block_redactions: List[Redaction] = []
            for s in clean_spans:
                prefix = _normalize_tag_prefix(s["entity_type"])
                cache_key = (prefix, s["original_text"].strip().lower())
                if cache_key not in value_to_tag:
                    counters[prefix] += 1
                    value_to_tag[cache_key] = self.tag_format.format(
                        prefix=prefix, index=counters[prefix]
                    )
                tag = value_to_tag[cache_key]

                red_obj = Redaction(
                    entity_type=s["entity_type"],
                    original_text=s["original_text"],
                    replacement=tag,
                    start=s["start"],
                    end=s["end"],
                    block_id=block.block_id,
                )
                block_redactions.append(red_obj)
                all_redactions.append(red_obj)

                traceability_log.append({
                    "document_id": document.document_id,
                    "file": document.filename,
                    "file_type": document.file_type,
                    "page_or_slide": block.page_number,
                    "block_id": block.block_id,
                    "block_type": block.metadata.get("block_type", "paragraph"),
                    "position": block.metadata.get("position"),
                    "pii_type": s["entity_type"],
                    "tag": tag,
                    "original_text": s["original_text"],
                    "start": s["start"],
                    "end": s["end"],
                    "detector": s["detector"],
                    "confidence": round(s["confidence"], 4),
                })

            new_text = block.text
            for r in reversed(block_redactions):
                new_text = new_text[: r.start] + r.replacement + new_text[r.end :]
            block.text = new_text
            block.metadata["redacted"] = True
            block.metadata["redaction_count"] = len(block_redactions)

        redacted_doc.metadata["is_redacted"] = True
        redacted_doc.metadata["total_redactions"] = len(all_redactions)
        redacted_text = "\n\n".join(b.text for b in redacted_doc.blocks if b.text)

        return all_redactions, redacted_text, redacted_doc, traceability_log


def redact(
    document: Union[Document, str],
    entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
) -> Tuple[List[Redaction], str]:
    """Callable redactor function compatible with Member 1's PIIPipeline."""
    return PIIRedactor().redact(document, entities)


def redact_document(
    document: Document,
    entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
) -> Tuple[List[Redaction], str, Document, List[Dict[str, Any]]]:
    """Convenience function returning (redactions, redacted_text, redacted_doc, traceability_log)."""
    return PIIRedactor().redact_document(document, entities)


def redact_text(
    text: str,
    entities: List[Union[PIIEntity, PIIFinding, Dict[str, Any]]],
    block_id: Optional[str] = None,
) -> Tuple[List[Redaction], str]:
    """Convenience function returning (redactions, redacted_text) for a raw string."""
    return PIIRedactor().redact_text(text=text, entities=entities, block_id=block_id)