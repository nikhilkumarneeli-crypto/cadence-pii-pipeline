"""Common JSON Schema and Data Models for Member 3 PPTX Extraction Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Standardizes extracted PPTX blocks according to the team-wide schema:
{
  "file": str,
  "slide": int,
  "section": Optional[str],
  "block_id": str,
  "block_type": str,
  "text": str,
  "position": {"left": float, "top": float, "width": float, "height": float},
  "order": int,
  "context_group_id": str,
  "source_type": str
}
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Dict, List
import json
from pathlib import Path


@dataclass
class Position:
    """Bounding box coordinates (in points or normalized units) for visual layout."""
    left: float = 0.0
    top: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "left": round(float(self.left), 2),
            "top": round(float(self.top), 2),
            "width": round(float(self.width), 2),
            "height": round(float(self.height), 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Position:
        return cls(
            left=float(data.get("left", 0.0)),
            top=float(data.get("top", 0.0)),
            width=float(data.get("width", 0.0)),
            height=float(data.get("height", 0.0)),
        )


@dataclass
class ExtractedBlock:
    """Single extracted content block conforming to the common team schema."""
    file: str
    slide: int
    section: Optional[str]
    block_id: str
    block_type: str  # "title", "text_box", "paragraph", "table", "table_cell", "chart_text", "speaker_notes", "image_ocr"
    text: str
    position: Position
    order: int
    context_group_id: str
    source_type: str  # "text_box", "table", "chart", "speaker_notes", "image_ocr", "grouped_shape"

    # Additional provenance and structural metadata
    slide_id: Optional[int] = None
    shape_id: Optional[int] = None
    parent_group_id: Optional[str] = None
    group_depth: int = 0
    confidence: float = 1.0
    paragraphs: List[str] = field(default_factory=list)
    table_metadata: Optional[Dict[str, Any]] = None
    chart_metadata: Optional[Dict[str, Any]] = None
    ocr_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching the common JSON schema."""
        d = {
            "file": self.file,
            "slide": self.slide,
            "section": self.section,
            "block_id": self.block_id,
            "block_type": self.block_type,
            "text": self.text,
            "position": self.position.to_dict(),
            "order": self.order,
            "context_group_id": self.context_group_id,
            "source_type": self.source_type,
            # Provenance metadata
            "slide_id": self.slide_id,
            "shape_id": self.shape_id,
            "parent_group_id": self.parent_group_id,
            "group_depth": self.group_depth,
            "confidence": round(float(self.confidence), 4),
            "paragraphs": self.paragraphs,
        }
        if self.table_metadata:
            d["table_metadata"] = self.table_metadata
        if self.chart_metadata:
            d["chart_metadata"] = self.chart_metadata
        if self.ocr_metadata:
            d["ocr_metadata"] = self.ocr_metadata
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExtractedBlock:
        pos_raw = d.get("position", {})
        pos = Position.from_dict(pos_raw) if isinstance(pos_raw, dict) else Position()
        return cls(
            file=d.get("file", ""),
            slide=d.get("slide", 1),
            section=d.get("section"),
            block_id=d.get("block_id", ""),
            block_type=d.get("block_type", "unknown"),
            text=d.get("text", ""),
            position=pos,
            order=d.get("order", 0),
            context_group_id=d.get("context_group_id", ""),
            source_type=d.get("source_type", "unknown"),
            slide_id=d.get("slide_id"),
            shape_id=d.get("shape_id"),
            parent_group_id=d.get("parent_group_id"),
            group_depth=d.get("group_depth", 0),
            confidence=float(d.get("confidence", 1.0)),
            paragraphs=d.get("paragraphs", []),
            table_metadata=d.get("table_metadata"),
            chart_metadata=d.get("chart_metadata"),
            ocr_metadata=d.get("ocr_metadata"),
        )


@dataclass
class SlideSummary:
    """Per-slide structural summary."""
    slide_number: int
    slide_id: Optional[int]
    total_blocks: int
    titles: List[str] = field(default_factory=list)
    has_tables: bool = False
    has_charts: bool = False
    has_images: bool = False
    has_notes: bool = False
    context_groups: List[str] = field(default_factory=list)


@dataclass
class PPTXExtractionResult:
    """Full extraction result for a PPTX presentation file."""
    file_name: str
    total_slides: int
    extracted_slides: int
    total_blocks: int
    blocks: List[ExtractedBlock]
    slide_summaries: List[SlideSummary] = field(default_factory=list)
    context_groups: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "total_slides": self.total_slides,
            "extracted_slides": self.extracted_slides,
            "total_blocks": self.total_blocks,
            "metadata": self.metadata,
            "slide_summaries": [asdict(s) for s in self.slide_summaries],
            "context_groups": self.context_groups,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    def save_json(self, output_path: str | Path) -> Path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return p

    @classmethod
    def load_json(cls, input_path: str | Path) -> PPTXExtractionResult:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        blocks = [ExtractedBlock.from_dict(b) for b in data.get("blocks", [])]
        summaries = [SlideSummary(**s) for s in data.get("slide_summaries", [])]
        return cls(
            file_name=data.get("file_name", ""),
            total_slides=data.get("total_slides", 0),
            extracted_slides=data.get("extracted_slides", 0),
            total_blocks=data.get("total_blocks", len(blocks)),
            blocks=blocks,
            slide_summaries=summaries,
            context_groups=data.get("context_groups", {}),
            metadata=data.get("metadata", {}),
        )
