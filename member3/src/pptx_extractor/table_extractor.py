"""Table Extractor for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Detects tables, extracts cells with exact row/column coordinates,
preserves cell bounding boxes, and builds structured table metadata.
"""

from __future__ import annotations
from typing import List, Tuple, Any, Dict
import pptx

from .schema import ExtractedBlock, Position
from .shape_extractor import emu_to_points, extract_shape_position


class TableExtractor:
    """Extracts tables and individual cells from PowerPoint slides."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def extract_from_table(
        self,
        shape: Any,
        slide_num: int,
        slide_id: int | None,
        table_index: int,
        order_counter: int,
    ) -> Tuple[List[ExtractedBlock], int]:
        """Extract table and its constituent cells.
        Returns a tuple of (blocks, updated_order_counter).
        """
        blocks: List[ExtractedBlock] = []
        table = shape.table
        num_rows = len(table.rows)
        num_cols = len(table.columns)

        table_pos = extract_shape_position(shape)
        table_ctx_id = f"s{slide_num}_tbl_{table_index}"

        # Precompute row heights and column widths for cell bounding box calculation
        col_widths_pt = [emu_to_points(col.width) for col in table.columns]
        row_heights_pt = [emu_to_points(row.height) for row in table.rows]

        cells_data: List[Dict[str, Any]] = []
        cell_blocks: List[ExtractedBlock] = []

        # Extract cells row-by-row
        curr_top = table_pos.top
        for row_idx in range(num_rows):
            curr_left = table_pos.left
            row_height = row_heights_pt[row_idx] if row_idx < len(row_heights_pt) else 20.0
            row_ctx_id = f"{table_ctx_id}_row_{row_idx}"

            for col_idx in range(num_cols):
                col_width = col_widths_pt[col_idx] if col_idx < len(col_widths_pt) else 50.0
                cell = table.cell(row_idx, col_idx)
                cell_text = cell.text.strip()

                cell_pos = Position(
                    left=curr_left,
                    top=curr_top,
                    width=col_width,
                    height=row_height,
                )

                cell_info = {
                    "row": row_idx,
                    "column": col_idx,
                    "text": cell_text,
                    "is_header": (row_idx == 0),
                }
                cells_data.append(cell_info)

                if cell_text:
                    order_counter += 1
                    cell_block_id = f"s{slide_num}_tbl{table_index}_r{row_idx}_c{col_idx}"
                    cell_block = ExtractedBlock(
                        file=self.file_name,
                        slide=slide_num,
                        section=None,
                        block_id=cell_block_id,
                        block_type="table_cell",
                        text=cell_text,
                        position=cell_pos,
                        order=order_counter,
                        context_group_id=row_ctx_id,
                        source_type="table",
                        slide_id=slide_id,
                        shape_id=shape.shape_id,
                        table_metadata={
                            "table_index": table_index,
                            "row": row_idx,
                            "column": col_idx,
                            "is_header": (row_idx == 0),
                            "total_rows": num_rows,
                            "total_cols": num_cols,
                        },
                        confidence=1.0,
                    )
                    cell_blocks.append(cell_block)

                curr_left += col_width
            curr_top += row_height

        # Build full table composite text
        composite_rows: List[str] = []
        for r in range(num_rows):
            row_items = [table.cell(r, c).text.strip() for c in range(num_cols)]
            composite_rows.append(" | ".join(row_items))
        full_table_text = "\n".join(composite_rows)

        # Parent table container block
        order_counter += 1
        parent_table_block = ExtractedBlock(
            file=self.file_name,
            slide=slide_num,
            section=None,
            block_id=f"s{slide_num}_tbl_{table_index}",
            block_type="table",
            text=full_table_text,
            position=table_pos,
            order=order_counter,
            context_group_id=table_ctx_id,
            source_type="table",
            slide_id=slide_id,
            shape_id=shape.shape_id,
            table_metadata={
                "table_index": table_index,
                "rows_count": num_rows,
                "columns_count": num_cols,
                "cells": cells_data,
            },
            confidence=1.0,
        )

        blocks.append(parent_table_block)
        blocks.extend(cell_blocks)
        return blocks, order_counter
