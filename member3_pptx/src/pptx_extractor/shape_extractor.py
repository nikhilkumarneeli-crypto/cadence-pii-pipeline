"""Shape Extractor for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Handles text boxes, auto shapes, placeholders, titles, paragraphs,
and recursive grouped shapes traversal.
"""

from __future__ import annotations
from typing import List, Optional, Tuple, Any
import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Length

from .schema import ExtractedBlock, Position


def emu_to_points(emu_val: Any) -> float:
    """Convert PowerPoint English Metric Units (EMU) to standard points (1 pt = 12700 EMU)."""
    if emu_val is None:
        return 0.0
    try:
        return round(float(emu_val) / 12700.0, 2)
    except (ValueError, TypeError):
        return 0.0


def extract_shape_position(shape: Any) -> Position:
    """Extract standard bounding box position in points from a shape."""
    return Position(
        left=emu_to_points(getattr(shape, "left", 0)),
        top=emu_to_points(getattr(shape, "top", 0)),
        width=emu_to_points(getattr(shape, "width", 0)),
        height=emu_to_points(getattr(shape, "height", 0)),
    )


def is_title_shape(shape: Any) -> bool:
    """Determine if a shape represents a slide title or header."""
    # 1. Check placeholder type if present
    if shape.is_placeholder:
        ph_format = shape.placeholder_format
        if ph_format.type in (
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
            PP_PLACEHOLDER.VERTICAL_TITLE,
        ):
            return True

    # 2. Heuristic check based on shape name and top position
    name_lower = shape.name.lower()
    if "title" in name_lower or "header" in name_lower:
        return True

    # 3. Position heuristic: top of slide with large font or short headline text
    top_pt = emu_to_points(getattr(shape, "top", 99999999))
    if top_pt < 120 and shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if 0 < len(text) < 120 and "\n" not in text:
            # Check font size of first paragraph if available
            try:
                first_p = shape.text_frame.paragraphs[0]
                if first_p.font.size and first_p.font.size.pt >= 20:
                    return True
            except Exception:
                pass
    return False


class ShapeExtractor:
    """Extracts text boxes, auto-shapes, and recursively processes grouped shapes."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def extract_from_shape(
        self,
        shape: Any,
        slide_num: int,
        slide_id: Optional[int],
        parent_group_id: Optional[str] = None,
        group_depth: int = 0,
        order_counter: int = 0,
    ) -> Tuple[List[ExtractedBlock], int]:
        """Extract content from a single shape or recursively from a group shape.
        Returns a tuple of (extracted_blocks, updated_order_counter).
        """
        blocks: List[ExtractedBlock] = []

        # 1. Handle Grouped Shapes Recursively
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP or hasattr(shape, "shapes"):
            current_group_id = f"s{slide_num}_grp_{shape.shape_id}"
            for child_idx, child_shape in enumerate(shape.shapes):
                child_blocks, order_counter = self.extract_from_shape(
                    shape=child_shape,
                    slide_num=slide_num,
                    slide_id=slide_id,
                    parent_group_id=current_group_id,
                    group_depth=group_depth + 1,
                    order_counter=order_counter,
                )
                blocks.extend(child_blocks)
            return blocks, order_counter

        # 2. Handle Text Frame Shapes (Text Boxes, AutoShapes, Placeholders)
        if shape.has_text_frame:
            text_frame = shape.text_frame
            full_text = text_frame.text.strip()
            if not full_text:
                return blocks, order_counter

            paragraphs = [p.text.strip() for p in text_frame.paragraphs if p.text.strip()]
            pos = extract_shape_position(shape)
            is_title = is_title_shape(shape)
            block_type = "title" if is_title else "text_box"
            source_type = "grouped_shape" if parent_group_id else "text_box"

            order_counter += 1
            block_id = f"s{slide_num}_b{order_counter}_sh{shape.shape_id}"
            ctx_group_id = parent_group_id if parent_group_id else f"s{slide_num}_cg_{order_counter}"

            block = ExtractedBlock(
                file=self.file_name,
                slide=slide_num,
                section=None,
                block_id=block_id,
                block_type=block_type,
                text=full_text,
                position=pos,
                order=order_counter,
                context_group_id=ctx_group_id,
                source_type=source_type,
                slide_id=slide_id,
                shape_id=shape.shape_id,
                parent_group_id=parent_group_id,
                group_depth=group_depth,
                confidence=1.0,
                paragraphs=paragraphs,
            )
            blocks.append(block)

        return blocks, order_counter
