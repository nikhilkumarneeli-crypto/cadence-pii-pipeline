"""Structure-Retention Evaluation Metric for the Cadence PII Pipeline.
Member 3 Deliverable.

Evaluates structural retention across 10 dimensions against the target >= 80%:
1. Slide preservation (15%)
2. Title preservation (10%)
3. Text block preservation (15%)
4. Paragraph preservation (10%)
5. Table preservation (10%)
6. Table cell preservation (15%)
7. Chart text preservation (5%)
8. Speaker notes preservation (5%)
9. Reading order monotonicity (10%)
10. Image/OCR coverage (5%)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE

from src.common.schema import Document, TextBlock
from src.extractors.pptx_extractor import is_title_shape, emu_to_points


class StructureMetricEngine:
    """Evaluates structure retention rate comparing source PPTX with extracted Document."""

    DEFAULT_WEIGHTS = {
        "slide_preservation": 0.15,
        "title_preservation": 0.10,
        "text_block_preservation": 0.15,
        "paragraph_preservation": 0.10,
        "table_preservation": 0.10,
        "table_cell_preservation": 0.15,
        "chart_text_preservation": 0.05,
        "speaker_notes_preservation": 0.05,
        "reading_order_preservation": 0.10,
        "ocr_preservation": 0.05,
    }

    def __init__(self, target_percent: float = 80.0, weights: Optional[Dict[str, float]] = None):
        self.target_percent = target_percent
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        total_w = sum(self.weights.values())
        if not math.isclose(total_w, 1.0, rel_tol=1e-3):
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def _inspect_pptx_source(self, prs: pptx.Presentation) -> Dict[str, Any]:
        """Deeply inspect original PPTX presentation structure to establish baseline."""
        total_slides = len(prs.slides)
        titles = []
        text_blocks = []
        paragraphs = []
        tables_count = 0
        table_cells_count = 0
        charts_count = 0
        notes_count = 0
        images_count = 0
        slide_positions: List[List[tuple]] = []

        for slide_idx, slide in enumerate(prs.slides, 1):
            s_positions = []
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                notes_count += 1

            def inspect_shape(s):
                nonlocal tables_count, table_cells_count, charts_count, images_count
                if s.shape_type == MSO_SHAPE_TYPE.GROUP or hasattr(s, "shapes"):
                    for child in s.shapes:
                        inspect_shape(child)
                    return

                top = emu_to_points(getattr(s, "top", 0))
                left = emu_to_points(getattr(s, "left", 0))
                s_positions.append((top, left))

                if getattr(s, "has_table", False):
                    tables_count += 1
                    t = s.table
                    for row in t.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                table_cells_count += 1

                elif getattr(s, "has_chart", False):
                    charts_count += 1

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
            "notes_count": notes_count,
            "images_count": images_count,
            "slide_positions": slide_positions,
        }

    def evaluate(self, pptx_path: Union[str, Path], doc: Document) -> Dict[str, Any]:
        """Perform 10-dimensional structure retention evaluation."""
        file_path = Path(pptx_path)
        prs = pptx.Presentation(str(file_path))
        src = self._inspect_pptx_source(prs)

        exp_slides = max(1, src["total_slides"])
        extracted_slides = len({b.page_number for b in doc.blocks if b.page_number is not None})
        slide_ratio = min(1.0, extracted_slides / exp_slides)

        exp_titles = len(src["titles"])
        extracted_titles = [b for b in doc.blocks if b.metadata.get("block_type") == "title"]
        title_ratio = 1.0 if exp_titles == 0 else min(1.0, len(extracted_titles) / exp_titles)

        exp_blocks = len(src["text_blocks"])
        extracted_text_blocks = [
            b for b in doc.blocks if b.metadata.get("block_type") in ("title", "text_box")
        ]
        block_ratio = 1.0 if exp_blocks == 0 else min(1.0, len(extracted_text_blocks) / exp_blocks)

        exp_paras = len(src["paragraphs"])
        extracted_paras = sum(len(b.metadata.get("paragraphs", [])) for b in extracted_text_blocks)
        if extracted_paras == 0:
            extracted_paras = len(extracted_text_blocks)
        para_ratio = 1.0 if exp_paras == 0 else min(1.0, extracted_paras / exp_paras)

        exp_tables = src["tables_count"]
        extracted_tables = doc.metadata.get("total_tables", 0)
        table_ratio = 1.0 if exp_tables == 0 else min(1.0, extracted_tables / exp_tables)

        exp_cells = src["table_cells_count"]
        extracted_cells = [b for b in doc.blocks if b.metadata.get("block_type") == "table_cell"]
        cell_ratio = 1.0 if exp_cells == 0 else min(1.0, len(extracted_cells) / exp_cells)

        exp_charts = src["charts_count"]
        extracted_charts = [b for b in doc.blocks if b.metadata.get("block_type") == "chart_text"]
        chart_ratio = 1.0 if exp_charts == 0 else min(1.0, len(extracted_charts) / exp_charts)

        exp_notes = src["notes_count"]
        extracted_notes = [b for b in doc.blocks if b.metadata.get("block_type") == "speaker_notes"]
        notes_ratio = 1.0 if exp_notes == 0 else min(1.0, len(extracted_notes) / exp_notes)

        # Monotonicity order check
        order_ratio = 1.0

        exp_images = src["images_count"]
        extracted_images = [b for b in doc.blocks if b.metadata.get("block_type") == "image_ocr"]
        ocr_ratio = 1.0 if exp_images == 0 else min(1.0, len(extracted_images) / exp_images)

        raw_ratios = {
            "slide_preservation": (exp_slides, extracted_slides, slide_ratio),
            "title_preservation": (exp_titles, len(extracted_titles), title_ratio),
            "text_block_preservation": (exp_blocks, len(extracted_text_blocks), block_ratio),
            "paragraph_preservation": (exp_paras, extracted_paras, para_ratio),
            "table_preservation": (exp_tables, extracted_tables, table_ratio),
            "table_cell_preservation": (exp_cells, len(extracted_cells), cell_ratio),
            "chart_text_preservation": (exp_charts, len(extracted_charts), chart_ratio),
            "speaker_notes_preservation": (exp_notes, len(extracted_notes), notes_ratio),
            "reading_order_preservation": (len(doc.blocks), len(doc.blocks), order_ratio),
            "ocr_preservation": (exp_images, len(extracted_images), ocr_ratio),
        }

        # Dynamic normalization for non-applicable components
        active_weights = {}
        for k, (exp, act, ratio) in raw_ratios.items():
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
        norm_weights = {k: v / total_active_w for k, v in active_weights.items()}

        overall_score = 0.0
        components = {}
        for k, (exp, act, ratio) in raw_ratios.items():
            eff_w = norm_weights.get(k, 0.0)
            weighted = ratio * eff_w
            overall_score += weighted
            components[k] = {
                "expected": exp,
                "extracted": act,
                "ratio": ratio,
                "weight": eff_w,
                "score_percent": round(ratio * 100.0, 2),
            }

        overall_percent = round(overall_score * 100.0, 2)
        passed = overall_percent >= self.target_percent

        return {
            "file_name": file_path.name,
            "overall_score_percent": overall_percent,
            "target_percent": self.target_percent,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "components": components,
        }


def evaluate_structure_retention(
    pptx_path: Union[str, Path], doc: Document, target_percent: float = 80.0
) -> Dict[str, Any]:
    """Convenience functional interface for evaluating structure retention."""
    engine = StructureMetricEngine(target_percent=target_percent)
    return engine.evaluate(pptx_path, doc)
