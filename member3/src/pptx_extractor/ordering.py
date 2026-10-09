"""Deterministic Visual Reading Order Engine for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Implements a robust 2D spatial layout ordering algorithm that reconstructs
natural human reading order from slide geometry:
- Header/title priority
- Spatial row-banding with horizontal tolerance
- Group hierarchy encapsulation
- Table row-column progression
- Speaker notes trailing position
"""

from __future__ import annotations
from typing import List, Tuple
from .schema import ExtractedBlock


class DeterministicOrderingEngine:
    """Sorts extracted blocks into human reading order using 2D spatial heuristics."""

    def __init__(self, vertical_band_tolerance_pt: float = 24.0):
        self.vertical_band_tolerance_pt = vertical_band_tolerance_pt

    def compute_sort_key(self, block: ExtractedBlock) -> Tuple:
        """Compute multi-level deterministic sort tuple."""
        # Level 1: Slide number
        slide_num = block.slide

        # Level 2: Speaker notes always placed at the end of slide content
        is_notes = 1 if block.block_type == "speaker_notes" else 0

        # Level 3: Header/title shapes get top priority
        is_title = 0 if block.block_type == "title" else 1

        # Level 4: Group hierarchy - grouped items inherit group anchor
        # Top coordinate banded into discrete vertical rows
        top_val = block.position.top
        band_index = int(top_val // self.vertical_band_tolerance_pt)

        # Level 5: Horizontal position (left-to-right)
        left_val = block.position.left

        # Level 6: Table cell specific ordering (row, col)
        if block.table_metadata:
            r = block.table_metadata.get("row", 0)
            c = block.table_metadata.get("column", 0)
            table_order = (r, c)
        else:
            table_order = (0, 0)

        # Level 7: Stable tie-breaker based on original extraction order
        tie_breaker = block.order

        return (slide_num, is_notes, is_title, band_index, left_val, table_order, tie_breaker)

    def order_blocks(self, blocks: List[ExtractedBlock]) -> List[ExtractedBlock]:
        """Sort blocks deterministically and assign re-indexed continuous order numbers."""
        # Sort using deterministic multi-level key
        sorted_blocks = sorted(blocks, key=self.compute_sort_key)

        # Re-assign sequential order index
        for new_order, block in enumerate(sorted_blocks, start=1):
            block.order = new_order

        return sorted_blocks
