"""PowerPoint (PPTX) Extractor for the Cadence PII Pipeline.
Member 3 Deliverable.

Extracts text boxes, titles, paragraphs, grouped shapes (recursively),
tables (cells & coordinates), charts, speaker notes, and embedded images.
Conforms to src.common.schema (Document, TextBlock).
"""

from __future__ import annotations

import os
import io
import math
import shutil
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Length

from src.common.schema import Document, TextBlock

logger = logging.getLogger(__name__)


def emu_to_points(emu_val: Any) -> float:
    """Convert PowerPoint English Metric Units (EMU) to standard points (1 pt = 12700 EMU)."""
    if emu_val is None:
        return 0.0
    try:
        return round(float(emu_val) / 12700.0, 2)
    except (ValueError, TypeError):
        return 0.0


def extract_shape_position(shape: Any) -> Dict[str, float]:
    """Extract standard bounding box position in points from a shape."""
    return {
        "left": emu_to_points(getattr(shape, "left", 0)),
        "top": emu_to_points(getattr(shape, "top", 0)),
        "width": emu_to_points(getattr(shape, "width", 0)),
        "height": emu_to_points(getattr(shape, "height", 0)),
    }


def is_title_shape(shape: Any) -> bool:
    """Determine if a shape represents a slide title or header."""
    if shape.is_placeholder:
        ph_format = shape.placeholder_format
        if ph_format.type in (
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
            PP_PLACEHOLDER.VERTICAL_TITLE,
        ):
            return True

    name_lower = shape.name.lower()
    if "title" in name_lower or "header" in name_lower:
        return True

    top_pt = emu_to_points(getattr(shape, "top", 99999999))
    if top_pt < 120 and shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if 0 < len(text) < 120 and "\n" not in text:
            try:
                first_p = shape.text_frame.paragraphs[0]
                if first_p.font.size and first_p.font.size.pt >= 20:
                    return True
            except Exception:
                pass
    return False


class PPTXExtractor:
    """Production PPTX extractor converting presentations into Document models."""

    def __init__(self, ocr_fn: Optional[Callable[[bytes], Tuple[str, float]]] = None, **kwargs: Any):
        self.ocr_fn = ocr_fn

    def extract(
        self, path: Union[str, Path], document_id: Optional[str] = None, **kwargs: Any
    ) -> Document:
        """Extract all content from a PowerPoint presentation into a normalized Document."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"PPTX file not found: {file_path}")

        try:
            prs = pptx.Presentation(str(file_path))
        except Exception as exc:
            raise ValueError(f"Failed to parse PPTX file '{file_path.name}': {exc}") from exc

        doc_id = document_id or file_path.stem
        blocks: List[TextBlock] = []
        global_order = 0

        total_tables = 0
        total_charts = 0
        total_notes = 0
        total_images = 0

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_id = getattr(slide, "slide_id", None)
            slide_raw_blocks: List[Tuple[TextBlock, float, float, int]] = []

            # 1. Process visual shapes
            table_idx = 0
            chart_idx = 0
            image_idx = 0

            for shape in slide.shapes:
                # A. Table Shape
                if getattr(shape, "has_table", False):
                    table_idx += 1
                    total_tables += 1
                    t_pos = extract_shape_position(shape)
                    t_shape = shape.table
                    num_rows = len(t_shape.rows)
                    num_cols = len(t_shape.columns)
                    table_ctx = f"s{slide_idx}_tbl_{table_idx}"

                    col_widths = [emu_to_points(c.width) for c in t_shape.columns]
                    row_heights = [emu_to_points(r.height) for r in t_shape.rows]

                    curr_top = t_pos["top"]
                    for r_idx in range(num_rows):
                        curr_left = t_pos["left"]
                        r_h = row_heights[r_idx] if r_idx < len(row_heights) else 20.0
                        row_ctx = f"{table_ctx}_r{r_idx}"

                        for c_idx in range(num_cols):
                            c_w = col_widths[c_idx] if c_idx < len(col_widths) else 50.0
                            cell = t_shape.cell(r_idx, c_idx)
                            c_text = cell.text.strip()

                            if c_text:
                                global_order += 1
                                b_id = f"s{slide_idx}_tbl{table_idx}_r{r_idx}_c{c_idx}"
                                cell_pos = {
                                    "left": curr_left,
                                    "top": curr_top,
                                    "width": c_w,
                                    "height": r_h,
                                }
                                tb = TextBlock(
                                    block_id=b_id,
                                    text=c_text,
                                    page_number=slide_idx,
                                    metadata={
                                        "block_type": "table_cell",
                                        "source_type": "table",
                                        "table_index": table_idx,
                                        "row": r_idx,
                                        "column": c_idx,
                                        "is_header": (r_idx == 0),
                                        "position": cell_pos,
                                        "context_group_id": row_ctx,
                                        "slide_id": slide_id,
                                        "shape_id": shape.shape_id,
                                    },
                                )
                                slide_raw_blocks.append((tb, curr_top, curr_left, 1))

                            curr_left += c_w
                        curr_top += r_h

                # B. Chart Shape
                elif getattr(shape, "has_chart", False):
                    chart_idx += 1
                    total_charts += 1
                    c_pos = extract_shape_position(shape)
                    chart = shape.chart
                    lines: List[str] = []

                    if chart.has_title and chart.chart_title:
                        t_txt = chart.chart_title.text_frame.text.strip()
                        if t_txt:
                            lines.append(f"Chart Title: {t_txt}")

                    cats: List[str] = []
                    series_list: List[str] = []
                    for plot in chart.plots:
                        if hasattr(plot, "categories") and plot.categories:
                            for c in plot.categories:
                                lbl = getattr(c, "label", str(c)).strip()
                                if lbl and lbl not in cats:
                                    cats.append(lbl)
                        for s in plot.series:
                            s_name = getattr(s, "name", "").strip()
                            if s_name and s_name not in series_list:
                                series_list.append(s_name)

                    if cats:
                        lines.append(f"Categories: {', '.join(cats)}")
                    if series_list:
                        lines.append(f"Series: {', '.join(series_list)}")

                    chart_text = "\n".join(lines) if lines else f"[Chart {chart_idx}]"
                    global_order += 1
                    tb = TextBlock(
                        block_id=f"s{slide_idx}_chart_{chart_idx}",
                        text=chart_text,
                        page_number=slide_idx,
                        metadata={
                            "block_type": "chart_text",
                            "source_type": "chart",
                            "chart_index": chart_idx,
                            "position": c_pos,
                            "context_group_id": f"s{slide_idx}_chart_{chart_idx}",
                            "categories": cats,
                            "series": series_list,
                            "slide_id": slide_id,
                            "shape_id": shape.shape_id,
                        },
                    )
                    slide_raw_blocks.append((tb, c_pos["top"], c_pos["left"], 1))

                # C. Picture / Image
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(shape, "image"):
                    image_idx += 1
                    total_images += 1
                    img_pos = extract_shape_position(shape)
                    img_text = ""
                    conf = 0.0
                    ocr_status = "unavailable"

                    if self.ocr_fn:
                        try:
                            img_text, conf = self.ocr_fn(shape.image.blob)
                            ocr_status = "processed"
                        except Exception as oe:
                            ocr_status = f"error: {oe}"

                    global_order += 1
                    tb = TextBlock(
                        block_id=f"s{slide_idx}_img_{image_idx}",
                        text=img_text,
                        page_number=slide_idx,
                        metadata={
                            "block_type": "image_ocr",
                            "source_type": "image_ocr",
                            "image_index": image_idx,
                            "position": img_pos,
                            "context_group_id": f"s{slide_idx}_img_{image_idx}",
                            "confidence": conf,
                            "ocr_status": ocr_status,
                            "slide_id": slide_id,
                            "shape_id": shape.shape_id,
                        },
                    )
                    slide_raw_blocks.append((tb, img_pos["top"], img_pos["left"], 2))

                # D. Text Box, Title, or Grouped Shapes
                else:
                    def parse_shape(s, parent_grp=None, depth=0):
                        nonlocal global_order
                        if s.shape_type == MSO_SHAPE_TYPE.GROUP or hasattr(s, "shapes"):
                            grp_id = f"s{slide_idx}_grp_{s.shape_id}"
                            for child in s.shapes:
                                parse_shape(child, parent_grp=grp_id, depth=depth + 1)
                            return

                        if s.has_text_frame:
                            txt = s.text_frame.text.strip()
                            if not txt:
                                return
                            s_pos = extract_shape_position(s)
                            is_title = is_title_shape(s)
                            b_type = "title" if is_title else "text_box"
                            s_type = "grouped_shape" if parent_grp else "text_box"
                            paras = [p.text.strip() for p in s.text_frame.paragraphs if p.text.strip()]

                            global_order += 1
                            b_id = f"s{slide_idx}_b{global_order}_sh{s.shape_id}"
                            ctx_id = parent_grp if parent_grp else f"s{slide_idx}_cg_{global_order}"

                            tb = TextBlock(
                                block_id=b_id,
                                text=txt,
                                page_number=slide_idx,
                                metadata={
                                    "block_type": b_type,
                                    "source_type": s_type,
                                    "position": s_pos,
                                    "context_group_id": ctx_id,
                                    "parent_group_id": parent_grp,
                                    "group_depth": depth,
                                    "paragraphs": paras,
                                    "slide_id": slide_id,
                                    "shape_id": s.shape_id,
                                },
                            )
                            tier = 0 if is_title else 1
                            slide_raw_blocks.append((tb, s_pos["top"], s_pos["left"], tier))

                    parse_shape(shape)

            # 2. Speaker Notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                total_notes += 1
                n_txt = slide.notes_slide.notes_text_frame.text.strip()
                n_paras = [p.text.strip() for p in slide.notes_slide.notes_text_frame.paragraphs if p.text.strip()]
                global_order += 1
                tb = TextBlock(
                    block_id=f"s{slide_idx}_notes",
                    text=n_txt,
                    page_number=slide_idx,
                    metadata={
                        "block_type": "speaker_notes",
                        "source_type": "speaker_notes",
                        "position": {"left": 0.0, "top": 1000.0, "width": 800.0, "height": 200.0},
                        "context_group_id": f"s{slide_idx}_notes",
                        "paragraphs": n_paras,
                        "slide_id": slide_id,
                    },
                )
                # Notes always placed last (tier 99)
                slide_raw_blocks.append((tb, 9999.0, 0.0, 99))

            # 3. Deterministic 2D Reading Order Sorting
            # (tier, vertical_band_index, left_coord)
            def sort_key(item):
                tb_obj, top_c, left_c, tier = item
                band_idx = int(top_c // 24.0)
                return (tier, band_idx, left_c)

            sorted_slide_blocks = sorted(slide_raw_blocks, key=sort_key)
            blocks.extend([item[0] for item in sorted_slide_blocks])

        # 4. Context Grouping & Entity Card Linking
        doc_metadata = {
            "total_slides": len(prs.slides),
            "total_blocks": len(blocks),
            "total_tables": total_tables,
            "total_charts": total_charts,
            "total_speaker_notes": total_notes,
            "total_images": total_images,
            "ordering_algorithm": "deterministic_2d_spatial_banding",
            "context_preservation": "spatial_proximity_clustering",
        }

        return Document(
            document_id=doc_id,
            filename=file_path.name,
            file_type="pptx",
            blocks=blocks,
            metadata=doc_metadata,
        )


def extract_pptx(path: Union[str, Path], **kwargs: Any) -> Document:
    """Convenience functional interface for extracting a PPTX presentation."""
    doc_id = kwargs.pop("document_id", None)
    ocr_fn = kwargs.pop("ocr_fn", None)
    extractor = PPTXExtractor(ocr_fn=ocr_fn, **kwargs)
    return extractor.extract(path, document_id=doc_id, **kwargs)
