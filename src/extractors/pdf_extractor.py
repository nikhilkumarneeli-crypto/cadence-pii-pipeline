 
"""PDF document extractor module for the cadence-pii-pipeline project (Member 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF
import numpy as np
import pdfplumber

from src.common.schema import Document, TextBlock
from src.extractors.ocr import LOW_CONFIDENCE_THRESHOLD, extract_ocr_blocks


class PDFExtractionError(ValueError):
    """Raised when an error occurs during PDF extraction or parsing."""
    pass


class PDFExtractor:
    """Extractor for digital and scanned PDF (.pdf) documents."""

    def __init__(
        self,
        include_empty: bool = False,
        min_digital_chars: int = 25,
        ocr_dpi: int = 300,
        low_conf_threshold: float = LOW_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.include_empty = include_empty
        self.min_digital_chars = min_digital_chars
        self.ocr_dpi = ocr_dpi
        self.low_conf_threshold = low_conf_threshold

    def extract(self, path: Union[str, Path], document_id: Optional[str] = None) -> Document:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a regular file: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Unsupported file extension '{file_path.suffix}'. Expected '.pdf'."
            )

        try:
            fitz_doc = fitz.open(file_path)
            plumber_pdf = pdfplumber.open(file_path)
        except Exception as exc:
            raise PDFExtractionError(
                f"Failed to read or parse PDF document '{file_path}': {exc}"
            ) from exc

        try:
            metadata = self._extract_metadata(file_path, fitz_doc)
            blocks: List[TextBlock] = []
            para_counter = 0
            table_counter = 0
            digital_pages = 0
            scanned_pages = 0
            order_index = 1

            for page_idx, (f_page, p_page) in enumerate(zip(fitz_doc, plumber_pdf.pages), start=1):
                native_text = f_page.get_text("text").strip()

                if len(native_text) < self.min_digital_chars:
                    scanned_pages += 1
                    pix = f_page.get_pixmap(dpi=self.ocr_dpi)
                    img_bytes = pix.tobytes("png")
                    ocr_blocks = extract_ocr_blocks(
                        image_input=img_bytes,
                        page_number=page_idx,
                        block_prefix=f"p{page_idx}_ocr_para",
                        start_order_index=order_index,
                        low_conf_threshold=self.low_conf_threshold,
                    )
                    for b in ocr_blocks:
                        if b.text or self.include_empty or b.metadata.get("ocr_status"):
                            blocks.append(b)
                            para_counter += 1
                            order_index += 1
                    continue

                digital_pages += 1
                page_elements: List[Tuple[float, float, List[TextBlock]]] = []

                tables = p_page.find_tables()
                table_bboxes = [t.bbox for t in tables]

                for tbl in tables:
                    tbl_blocks = self._extract_table_blocks(tbl, table_counter, page_idx)
                    if tbl_blocks:
                        x0, y0, _, _ = tbl.bbox
                        page_elements.append((float(y0), float(x0), tbl_blocks))
                        table_counter += 1

                text_elements, para_counter = self._extract_digital_text_blocks(
                    f_page, page_idx, table_bboxes, para_counter
                )
                page_elements.extend(text_elements)

                page_elements.sort(key=lambda item: (round(item[0] / 15.0), item[1]))

                for _, _, element_blocks in page_elements:
                    for blk in element_blocks:
                        blk.metadata["order_index"] = order_index
                        order_index += 1
                        blocks.append(blk)

        finally:
            plumber_pdf.close()
            fitz_doc.close()

        doc_id = document_id or f"doc_{file_path.stem}"
        low_conf_ids = [b.block_id for b in blocks if b.metadata.get("low_confidence_flag")]

        metadata["total_blocks"] = len(blocks)
        metadata["total_paragraphs"] = para_counter
        metadata["total_tables"] = table_counter
        metadata["digital_pages"] = digital_pages
        metadata["scanned_pages"] = scanned_pages
        metadata["low_confidence_block_ids"] = low_conf_ids

        return Document(
            document_id=doc_id,
            filename=file_path.name,
            file_type="pdf",
            blocks=blocks,
            metadata=metadata,
        )

    def _extract_metadata(self, file_path: Path, fitz_doc: fitz.Document) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "source_path": str(file_path.resolve()),
            "file_name": file_path.name,
            "file_size_bytes": file_path.stat().st_size,
            "page_count": len(fitz_doc),
        }
        try:
            pdf_meta = fitz_doc.metadata or {}
            if pdf_meta.get("title"):
                metadata["title"] = pdf_meta["title"]
            if pdf_meta.get("author"):
                metadata["author"] = pdf_meta["author"]
            if pdf_meta.get("creationDate"):
                metadata["created"] = pdf_meta["creationDate"]
            if pdf_meta.get("modDate"):
                metadata["modified"] = pdf_meta["modDate"]
        except Exception:
            pass
        return metadata

    def _extract_digital_text_blocks(
        self,
        f_page: fitz.Page,
        page_number: int,
        table_bboxes: List[Tuple[float, float, float, float]],
        para_counter: int,
    ) -> Tuple[List[Tuple[float, float, List[TextBlock]]], int]:
        raw_blocks = f_page.get_text("dict").get("blocks", [])
        font_sizes = [
            float(span["size"])
            for b in raw_blocks if b.get("type") == 0
            for line in b.get("lines", [])
            for span in line.get("spans", [])
            if span.get("text", "").strip()
        ]
        median_font = float(np.median(font_sizes)) if font_sizes else 11.0
        elements: List[Tuple[float, float, List[TextBlock]]] = []

        for b in raw_blocks:
            if b.get("type") != 0:
                continue
            bx0, by0, bx1, by1 = b["bbox"]
            cx, cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0

            if any(tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3] for tb in table_bboxes):
                continue

            lines_text: List[str] = []
            max_font = 0.0
            is_bold = False
            spans_count = 0

            for line in b.get("lines", []):
                spans = line.get("spans", [])
                line_str = " ".join(s["text"].strip() for s in spans if s.get("text", "").strip())
                if line_str:
                    lines_text.append(line_str)
                for s in spans:
                    spans_count += 1
                    max_font = max(max_font, float(s.get("size", 11.0)))
                    font_name = str(s.get("font", "")).lower()
                    if "bold" in font_name or (int(s.get("flags", 0)) & 16):
                        is_bold = True

            full_text = "\n".join(lines_text).strip()
            if not full_text and not self.include_empty:
                continue

            is_heading = (max_font >= median_font * 1.15) or (
                is_bold and len(lines_text) == 1 and len(full_text) < 90
            )
            heading_level = None
            if is_heading:
                heading_level = 1 if max_font >= median_font * 1.35 else 2

            para_id = f"para_{para_counter}"
            para_counter += 1

            block = TextBlock(
                block_id=para_id,
                text=full_text,
                page_number=page_number,
                metadata={
                    "block_type": "paragraph",
                    "source_type": "pdf_text",
                    "style": "Heading" if is_heading else "Normal",
                    "is_heading": is_heading,
                    "heading_level": heading_level,
                    "font_size": round(max_font, 1),
                    "runs_count": spans_count,
                    "position": {
                        "left": round(float(bx0), 1),
                        "top": round(float(by0), 1),
                        "width": round(float(bx1 - bx0), 1),
                        "height": round(float(by1 - by0), 1),
                    },
                    "confidence": 1.0,
                    "low_confidence_flag": False,
                },
            )
            elements.append((float(by0), float(bx0), [block]))

        return elements, para_counter

    def _extract_table_blocks(
        self, tbl: Any, table_index: int, page_number: int
    ) -> List[TextBlock]:
        rows = tbl.extract()
        if not rows:
            return []

        x0, y0, x1, y1 = tbl.bbox
        headers = [str(c).strip().replace("\n", " ") if c else "" for c in rows[0]]
        blocks: List[TextBlock] = []

        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                cell_text = str(cell).strip() if cell is not None else ""
                if not cell_text and not self.include_empty:
                    continue

                col_header = headers[c_idx] if c_idx < len(headers) else ""
                blocks.append(
                    TextBlock(
                        block_id=f"tbl_{table_index}_r{r_idx}_c{c_idx}",
                        text=cell_text,
                        page_number=page_number,
                        metadata={
                            "block_type": "table_cell",
                            "source_type": "pdf_table",
                            "table_index": table_index,
                            "row_index": r_idx,
                            "col_index": c_idx,
                            "column_header": col_header,
                            "position": {
                                "left": round(float(x0), 1),
                                "top": round(float(y0) + r_idx * 12.0, 1),
                                "width": round(float(x1 - x0), 1),
                                "height": 12.0,
                            },
                            "confidence": 1.0,
                            "low_confidence_flag": False,
                        },
                    )
                )

        return blocks


def extract_pdf(path: Union[str, Path], document_id: Optional[str] = None, **kwargs: Any) -> Document:
    return PDFExtractor(**kwargs).extract(path=path, document_id=document_id)


extract = extract_pdf
 