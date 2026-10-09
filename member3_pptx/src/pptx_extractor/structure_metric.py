"""Structure-Retention Metric Engine for Member 3.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Implements an objective, multi-component structural preservation evaluation
comparing original PPTX geometry and content against extracted representation.
Evaluates against the project requirement: Target >= 80%.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE

from .schema import PPTXExtractionResult, ExtractedBlock
from .shape_extractor import is_title_shape, emu_to_points


@dataclass
class ComponentScore:
    """Detailed score for an individual structural dimension."""
    component_name: str
    expected_count: int
    extracted_count: int
    raw_ratio: float
    weight: float
    effective_weight: float
    weighted_score: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "expected_count": self.expected_count,
            "extracted_count": self.extracted_count,
            "score_percent": round(self.raw_ratio * 100.0, 2),
            "configured_weight": round(self.weight, 4),
            "effective_weight": round(self.effective_weight, 4),
            "weighted_score_percent": round(self.weighted_score * 100.0, 2),
            "description": self.description,
        }


@dataclass
class SlideEvaluation:
    """Per-slide structural breakdown."""
    slide_number: int
    score_percent: float
    blocks_count: int
    has_title: bool
    has_table: bool
    has_chart: bool
    has_notes: bool


@dataclass
class EvaluationResult:
    """Complete structural evaluation report for a PPTX file."""
    file_name: str
    target_percent: float
    overall_score_percent: float
    passed: bool
    status: str  # "PASS" or "FAIL"
    total_slides: int
    component_scores: Dict[str, ComponentScore]
    per_slide_evaluations: List[SlideEvaluation]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "target_percent": self.target_percent,
            "overall_score_percent": round(self.overall_score_percent, 2),
            "status": self.status,
            "passed": self.passed,
            "total_slides": self.total_slides,
            "component_scores": {k: v.to_dict() for k, v in self.component_scores.items()},
            "per_slide_evaluations": [asdict(s) for s in self.per_slide_evaluations],
            "notes": self.notes,
        }


class StructureMetricEngine:
    """Evaluates structural retention of extracted PPTX against ground truth or source file."""

    DEFAULT_WEIGHTS = {
        "slide_preservation": 0.15,       # Macro document segmentation
        "title_preservation": 0.10,       # Semantic section titles
        "text_block_preservation": 0.15,  # Text containers
        "paragraph_preservation": 0.10,   # Micro text boundaries
        "table_preservation": 0.10,       # Tabular structure detection
        "table_cell_preservation": 0.15,  # Exact 2D grid cells & text
        "chart_text_preservation": 0.05,  # Chart title, series & categories
        "speaker_notes_preservation": 0.05, # Presentation speaker notes
        "reading_order_preservation": 0.10, # 2D layout reading order
        "ocr_preservation": 0.05,         # Embedded image text extraction
    }

    def __init__(
        self,
        target_percent: float = 80.0,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.target_percent = target_percent
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        # Verify weight total
        total_w = sum(self.weights.values())
        if not math.isclose(total_w, 1.0, rel_tol=1e-3):
            # Normalize to 1.0
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def _inspect_pptx_source(self, prs: pptx.Presentation) -> Dict[str, Any]:
        """Deeply inspect original PPTX presentation structure to establish ground truth."""
        total_slides = len(prs.slides)
        titles: List[str] = []
        text_blocks: List[str] = []
        paragraphs: List[str] = []
        tables_count = 0
        table_cells_count = 0
        charts_count = 0
        chart_elements_count = 0
        notes_count = 0
        images_count = 0
        slide_positions: List[List[tuple]] = []

        for slide_idx, slide in enumerate(prs.slides, 1):
            s_positions = []

            # Notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                notes_count += 1

            def inspect_shape(s):
                nonlocal tables_count, table_cells_count, charts_count, chart_elements_count, images_count
                if s.shape_type == MSO_SHAPE_TYPE.GROUP or hasattr(s, "shapes"):
                    for child in s.shapes:
                        inspect_shape(child)
                    return

                # Record geometric position (top, left)
                top = emu_to_points(getattr(s, "top", 0))
                left = emu_to_points(getattr(s, "left", 0))
                s_positions.append((top, left))

                if getattr(s, "has_table", False):
                    tables_count += 1
                    t = s.table
                    for row in t.rows:
                        for cell in row.cells:
                            c_txt = cell.text.strip()
                            if c_txt:
                                table_cells_count += 1

                elif getattr(s, "has_chart", False):
                    charts_count += 1
                    c = s.chart
                    if c.has_title and c.chart_title:
                        chart_elements_count += 1
                    for plot in c.plots:
                        if hasattr(plot, "categories") and plot.categories:
                            chart_elements_count += len(plot.categories)
                        for series in plot.series:
                            chart_elements_count += 1

                elif s.shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(s, "image"):
                    images_count += 1

                elif s.has_text_frame:
                    t_frame = s.text_frame
                    txt = t_frame.text.strip()
                    if txt:
                        text_blocks.append(txt)
                        if is_title_shape(s):
                            titles.append(txt.split("\n")[0])
                        for p in t_frame.paragraphs:
                            if p.text.strip():
                                paragraphs.append(p.text.strip())

            for shape in slide.shapes:
                inspect_shape(shape)

            slide_positions.append(s_positions)

        return {
            "total_slides": total_slides,
            "titles": titles,
            "text_blocks": text_blocks,
            "paragraphs": paragraphs,
            "tables_count": tables_count,
            "table_cells_count": table_cells_count,
            "charts_count": charts_count,
            "chart_elements_count": chart_elements_count,
            "notes_count": notes_count,
            "images_count": images_count,
            "slide_positions": slide_positions,
        }

    def _compute_reading_order_preservation(
        self, original_positions: List[List[tuple]], extracted_blocks: List[ExtractedBlock]
    ) -> float:
        """Measure monotonicity of visual reading order using relative inversion score."""
        slide_scores: List[float] = []

        for slide_idx, positions in enumerate(original_positions, start=1):
            if len(positions) <= 1:
                slide_scores.append(1.0)
                continue

            # Extracted blocks for this slide (excluding notes)
            s_blocks = [
                b for b in extracted_blocks
                if b.slide == slide_idx and b.block_type != "speaker_notes"
            ]
            if len(s_blocks) <= 1:
                slide_scores.append(1.0)
                continue

            # Expected order is vertical top-down with 24pt horizontal banding
            expected_sorted = sorted(
                enumerate(s_blocks),
                key=lambda item: (
                    0 if item[1].block_type == "title" else 1,
                    int(item[1].position.top // 24.0),
                    item[1].position.left,
                )
            )

            # Check Kendall tau / inversion count
            extracted_ranks = [item[0] for item in expected_sorted]
            inversions = 0
            n = len(extracted_ranks)
            total_pairs = n * (n - 1) / 2
            if total_pairs == 0:
                slide_scores.append(1.0)
                continue

            for i in range(n):
                for j in range(i + 1, n):
                    if extracted_ranks[i] > extracted_ranks[j]:
                        inversions += 1

            concordance = 1.0 - (inversions / total_pairs)
            slide_scores.append(max(0.0, concordance))

        return sum(slide_scores) / len(slide_scores) if slide_scores else 1.0

    def evaluate(
        self,
        pptx_path: str | Path,
        extraction_result: PPTXExtractionResult,
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """Perform comprehensive structure retention evaluation."""
        file_path = Path(pptx_path)
        prs = pptx.Presentation(str(file_path))
        src = self._inspect_pptx_source(prs)

        # 1. Slide preservation
        exp_slides = max(1, src["total_slides"])
        act_slides = extraction_result.extracted_slides
        slide_ratio = min(1.0, act_slides / exp_slides)

        # 2. Title preservation
        exp_titles = len(src["titles"])
        extracted_titles = [b for b in extraction_result.blocks if b.block_type == "title"]
        act_titles = len(extracted_titles)
        title_ratio = 1.0 if exp_titles == 0 else min(1.0, act_titles / exp_titles)

        # 3. Text block preservation
        exp_blocks = len(src["text_blocks"])
        extracted_text_blocks = [
            b for b in extraction_result.blocks
            if b.block_type in ("title", "text_box", "paragraph")
        ]
        act_blocks = len(extracted_text_blocks)
        block_ratio = 1.0 if exp_blocks == 0 else min(1.0, act_blocks / exp_blocks)

        # 4. Paragraph preservation
        exp_paras = len(src["paragraphs"])
        act_paras = sum(len(b.paragraphs) for b in extracted_text_blocks)
        if act_paras == 0:
            act_paras = act_blocks
        para_ratio = 1.0 if exp_paras == 0 else min(1.0, act_paras / exp_paras)

        # 5. Table preservation
        exp_tables = src["tables_count"]
        extracted_tables = [b for b in extraction_result.blocks if b.block_type == "table"]
        act_tables = len(extracted_tables)
        table_ratio = 1.0 if exp_tables == 0 else min(1.0, act_tables / exp_tables)

        # 6. Table cell preservation
        exp_cells = src["table_cells_count"]
        extracted_cells = [b for b in extraction_result.blocks if b.block_type == "table_cell"]
        act_cells = len(extracted_cells)
        cell_ratio = 1.0 if exp_cells == 0 else min(1.0, act_cells / exp_cells)

        # 7. Chart text preservation
        exp_charts = src["charts_count"]
        extracted_charts = [b for b in extraction_result.blocks if b.block_type == "chart_text"]
        act_charts = len(extracted_charts)
        chart_ratio = 1.0 if exp_charts == 0 else min(1.0, act_charts / exp_charts)

        # 8. Speaker notes preservation
        exp_notes = src["notes_count"]
        extracted_notes = [b for b in extraction_result.blocks if b.block_type == "speaker_notes"]
        act_notes = len(extracted_notes)
        notes_ratio = 1.0 if exp_notes == 0 else min(1.0, act_notes / exp_notes)

        # 9. Reading order preservation
        order_ratio = self._compute_reading_order_preservation(
            src["slide_positions"], extraction_result.blocks
        )

        # 10. OCR / Image preservation
        exp_images = src["images_count"]
        extracted_ocr = [b for b in extraction_result.blocks if b.block_type == "image_ocr"]
        act_ocr = len(extracted_ocr)
        ocr_ratio = 1.0 if exp_images == 0 else min(1.0, act_ocr / exp_images)

        # Assemble raw metrics
        raw_components = {
            "slide_preservation": (exp_slides, act_slides, slide_ratio, "Preservation of slide boundaries and counts"),
            "title_preservation": (exp_titles, act_titles, title_ratio, "Preservation of slide headers and section titles"),
            "text_block_preservation": (exp_blocks, act_blocks, block_ratio, "Preservation of body text frames and boxes"),
            "paragraph_preservation": (exp_paras, act_paras, para_ratio, "Preservation of discrete paragraph boundaries"),
            "table_preservation": (exp_tables, act_tables, table_ratio, "Detection and preservation of table structures"),
            "table_cell_preservation": (exp_cells, act_cells, cell_ratio, "Preservation of 2D table cells, rows, and columns"),
            "chart_text_preservation": (exp_charts, act_charts, chart_ratio, "Extraction of titles, categories, and series"),
            "speaker_notes_preservation": (exp_notes, act_notes, notes_ratio, "Preservation of slide speaker notes"),
            "reading_order_preservation": (len(extraction_result.blocks), len(extraction_result.blocks), order_ratio, "Visual reading-order monotonicity (Kendall's tau)"),
            "ocr_preservation": (exp_images, act_ocr, ocr_ratio, "Image detection and OCR text extraction coverage"),
        }

        # Dynamic re-weighting for non-applicable components
        active_weights: Dict[str, float] = {}
        for k, (exp, act, ratio, _) in raw_components.items():
            # If expected count is 0 and not slide/order, component is non-applicable
            if k in ("table_preservation", "table_cell_preservation") and exp_tables == 0:
                continue
            if k == "chart_text_preservation" and exp_charts == 0:
                continue
            if k == "speaker_notes_preservation" and exp_notes == 0:
                continue
            if k == "ocr_preservation" and exp_images == 0:
                continue
            active_weights[k] = self.weights[k]

        total_active_w = sum(active_weights.values())
        normalized_weights = {k: v / total_active_w for k, v in active_weights.items()}

        component_scores: Dict[str, ComponentScore] = {}
        overall_score = 0.0

        for k, (exp, act, ratio, desc) in raw_components.items():
            eff_w = normalized_weights.get(k, 0.0)
            weighted = ratio * eff_w
            overall_score += weighted

            component_scores[k] = ComponentScore(
                component_name=k,
                expected_count=exp,
                extracted_count=act,
                raw_ratio=ratio,
                weight=self.weights.get(k, 0.0),
                effective_weight=eff_w,
                weighted_score=weighted,
                description=desc,
            )

        overall_score_pct = round(overall_score * 100.0, 2)
        passed = overall_score_pct >= self.target_percent
        status = "PASS" if passed else "FAIL"

        # Per slide breakdown
        per_slide: List[SlideEvaluation] = []
        for s_idx in range(1, exp_slides + 1):
            s_blks = [b for b in extraction_result.blocks if b.slide == s_idx]
            has_title = any(b.block_type == "title" for b in s_blks)
            has_table = any(b.block_type == "table" for b in s_blks)
            has_chart = any(b.block_type == "chart_text" for b in s_blks)
            has_notes = any(b.block_type == "speaker_notes" for b in s_blks)
            s_score = 100.0 if s_blks else 0.0
            per_slide.append(
                SlideEvaluation(
                    slide_number=s_idx,
                    score_percent=s_score,
                    blocks_count=len(s_blks),
                    has_title=has_title,
                    has_table=has_table,
                    has_chart=has_chart,
                    has_notes=has_notes,
                )
            )

        notes = []
        if passed:
            notes.append(f"Structure retention ({overall_score_pct}%) exceeds the >= {self.target_percent}% threshold.")
        else:
            notes.append(f"Structure retention ({overall_score_pct}%) is below the {self.target_percent}% target.")

        if exp_images > 0 and act_ocr == 0:
            notes.append("Images detected on slides but OCR produced no text (check Tesseract availability).")

        return EvaluationResult(
            file_name=file_path.name,
            target_percent=self.target_percent,
            overall_score_percent=overall_score_pct,
            passed=passed,
            status=status,
            total_slides=exp_slides,
            component_scores=component_scores,
            per_slide_evaluations=per_slide,
            notes=notes,
        )
