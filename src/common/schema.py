"""Common schema definitions for the cadence-pii-pipeline project.

Provides dependency-light, typed dataclasses used across all pipeline stages:
- Extraction (Members 1, 2, 3)
- Detection (Member 4)
- Redaction and Reporting (Member 5)
- Orchestration and Routing (Member 1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextBlock:
    """Represents a coherent segment of text extracted from a document.

    Attributes:
        block_id: Unique, stable identifier for this block within the document.
        text: The raw extracted text content.
        page_number: Optional 1-based page index (e.g. for PDF/PPTX; DOCX may be None).
        metadata: Arbitrary extractor-specific or structural metadata
                  (e.g. style, heading level, table coordinates, bounding box).
    """

    block_id: str
    text: str
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Represents an ingested document normalized into standard text blocks.

    Attributes:
        document_id: Unique identifier for the document instance.
        filename: Original file name or path reference.
        file_type: Canonical file type extension (e.g. 'docx', 'pdf', 'pptx').
        blocks: Ordered list of extracted TextBlock objects.
        metadata: Document-level metadata (e.g. author, created date, page count).
    """

    document_id: str
    filename: str
    file_type: str
    blocks: List[TextBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Convenience property returning all block texts joined by newlines."""
        return self.get_text()

    def get_text(self, separator: str = "\n\n") -> str:
        """Returns all document text by concatenating blocks with the given separator.

        Args:
            separator: String delimiter placed between block texts. Defaults to double newline.

        Returns:
            Concatenated document text.
        """
        return separator.join(b.text for b in self.blocks if b.text)


@dataclass
class PIIEntity:
    """Represents a single detected Personally Identifiable Information (PII) entity.

    Attributes:
        entity_type: Category/taxonomy of the entity (e.g. 'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER').
        text: The specific text identified as PII.
        start: Start character offset of the entity.
        end: End character offset of the entity (exclusive).
        confidence: Detection confidence score between 0.0 and 1.0. Defaults to 1.0.
        block_id: Optional ID of the TextBlock where this entity was located.
        metadata: Additional detection details (e.g. recognition rule, Presidio recognizer name).
    """

    entity_type: str
    text: str
    start: int
    end: int
    confidence: float = 1.0
    block_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Redaction:
    """Represents a redaction action performed or planned on sensitive text.

    Attributes:
        entity_type: Category of the redacted entity.
        original_text: The original sensitive text that was redacted.
        replacement: The replacement text or mask (e.g. '[REDACTED]', '<EMAIL_ADDRESS>', '***').
        start: Start character offset of the redacted span.
        end: End character offset of the redacted span.
        block_id: Optional ID of the TextBlock where the redaction took place.
    """

    entity_type: str
    original_text: str
    replacement: str
    start: int
    end: int
    block_id: Optional[str] = None


@dataclass
class PipelineResult:
    """Represents the end-to-end outcome of document processing.

    Attributes:
        document: The original extracted Document model.
        detected_entities: List of PIIEntity instances identified by the detector.
        redactions: List of Redaction operations performed.
        redacted_text: Full document text after applying redactions (if redaction was run).
        metadata: Execution statistics, timing, or pipeline configuration info.
    """

    document: Document
    detected_entities: List[PIIEntity] = field(default_factory=list)
    redactions: List[Redaction] = field(default_factory=list)
    redacted_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
