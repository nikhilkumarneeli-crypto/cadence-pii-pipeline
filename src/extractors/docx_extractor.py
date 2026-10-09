"""DOCX document extractor module for the cadence-pii-pipeline project.

Extracts text content and structural elements (paragraphs, tables) from .docx files,
normalizing them into the common Document and TextBlock schema without modifying
or redacting any underlying text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

from src.common.schema import Document, TextBlock


class DocxExtractionError(ValueError):
    """Raised when an error occurs during DOCX extraction or parsing."""
    pass


class DocxExtractor:
    """Extractor for Microsoft Word (.docx) documents."""

    def __init__(self, include_empty: bool = False):
        """Initializes the DOCX extractor.

        Args:
            include_empty: Whether to include empty/whitespace-only paragraphs. Defaults to False.
        """
        self.include_empty = include_empty

    def extract(self, path: Union[str, Path], document_id: Optional[str] = None) -> Document:
        """Extracts structured text blocks from a DOCX file.

        Args:
            path: Path to the .docx file (str or Path).
            document_id: Optional explicit document identifier. Defaults to 'doc_<file_stem>'.

        Returns:
            A common Document instance containing ordered TextBlock objects.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file path is invalid or extension is not .docx.
            DocxExtractionError: If the file cannot be opened or parsed as a valid DOCX document.
        """
        file_path = Path(path)

        # 1. Validation
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a regular file: {file_path}")

        if file_path.suffix.lower() != ".docx":
            raise ValueError(
                f"Unsupported file extension '{file_path.suffix}'. Expected '.docx'."
            )

        # 2. Parse DOCX using python-docx
        try:
            doc = docx.Document(file_path)
        except Exception as exc:
            raise DocxExtractionError(
                f"Failed to read or parse DOCX document '{file_path}': {exc}"
            ) from exc

        # 3. Extract metadata
        metadata = self._extract_metadata(file_path, doc)

        # 4. Extract blocks in document body order
        blocks: List[TextBlock] = []
        para_counter = 0
        table_counter = 0

        for child in doc.element.body:
            if isinstance(child, docx.oxml.text.paragraph.CT_P):
                p = Paragraph(child, doc)
                text = p.text if self.include_empty else p.text.strip()
                if not text and not self.include_empty:
                    continue

                para_id = f"para_{para_counter}"
                para_counter += 1
                para_meta = self._extract_paragraph_metadata(p, para_counter)
                blocks.append(
                    TextBlock(
                        block_id=para_id,
                        text=p.text.strip(),
                        page_number=None,
                        metadata=para_meta,
                    )
                )

            elif isinstance(child, docx.oxml.table.CT_Tbl):
                tbl = Table(child, doc)
                tbl_blocks = self._extract_table_blocks(tbl, table_counter)
                blocks.extend(tbl_blocks)
                table_counter += 1

        doc_id = document_id or f"doc_{file_path.stem}"

        metadata["total_blocks"] = len(blocks)
        metadata["total_paragraphs"] = para_counter
        metadata["total_tables"] = table_counter

        return Document(
            document_id=doc_id,
            filename=file_path.name,
            file_type="docx",
            blocks=blocks,
            metadata=metadata,
        )

    def _extract_metadata(self, file_path: Path, doc: docx.Document) -> Dict[str, Any]:
        """Extracts document-level core properties and file attributes."""
        metadata: Dict[str, Any] = {
            "source_path": str(file_path.resolve()),
            "file_name": file_path.name,
            "file_size_bytes": file_path.stat().st_size,
        }
        try:
            core_props = doc.core_properties
            if core_props:
                if core_props.title:
                    metadata["title"] = core_props.title
                if core_props.author:
                    metadata["author"] = core_props.author
                if core_props.created:
                    metadata["created"] = str(core_props.created)
                if core_props.modified:
                    metadata["modified"] = str(core_props.modified)
                if core_props.last_modified_by:
                    metadata["last_modified_by"] = core_props.last_modified_by
        except Exception:
            # Core properties extraction should be non-blocking
            pass

        return metadata

    def _extract_paragraph_metadata(self, p: Paragraph, order_index: int) -> Dict[str, Any]:
        """Extracts style and structural metadata for a paragraph."""
        style_name = getattr(p.style, "name", None)
        is_heading = False
        heading_level = None

        if style_name:
            lower_style = style_name.lower()
            if "heading" in lower_style:
                is_heading = True
                digits = [c for c in style_name if c.isdigit()]
                if digits:
                    try:
                        heading_level = int("".join(digits))
                    except ValueError:
                        heading_level = None
            elif "title" in lower_style:
                is_heading = True
                heading_level = 0

        alignment_str = None
        if p.alignment is not None:
            alignment_str = str(p.alignment)

        return {
            "block_type": "paragraph",
            "order_index": order_index,
            "style": style_name,
            "is_heading": is_heading,
            "heading_level": heading_level,
            "alignment": alignment_str,
            "runs_count": len(p.runs),
        }

    def _extract_table_blocks(self, tbl: Table, table_index: int) -> List[TextBlock]:
        """Extracts text blocks from table cells, preserving row/col structure and avoiding duplicates in merged cells."""
        blocks: List[TextBlock] = []
        seen_cells = set()

        for r_idx, row in enumerate(tbl.rows):
            for c_idx, cell in enumerate(row.cells):
                # Guard against duplicate cell references caused by cell merging in python-docx
                if cell._tc in seen_cells:
                    continue
                seen_cells.add(cell._tc)

                cell_text = cell.text.strip()
                if not cell_text and not self.include_empty:
                    continue

                blocks.append(
                    TextBlock(
                        block_id=f"tbl_{table_index}_r{r_idx}_c{c_idx}",
                        text=cell_text,
                        page_number=None,
                        metadata={
                            "block_type": "table_cell",
                            "table_index": table_index,
                            "row_index": r_idx,
                            "col_index": c_idx,
                        },
                    )
                )

        return blocks


def extract_docx(path: Union[str, Path], document_id: Optional[str] = None) -> Document:
    """Convenience function to extract a Document from a DOCX file.

    Args:
        path: Path to the .docx file (str or Path).
        document_id: Optional explicit document identifier.

    Returns:
        A Document instance containing extracted TextBlock objects.
    """
    return DocxExtractor().extract(path=path, document_id=document_id)
