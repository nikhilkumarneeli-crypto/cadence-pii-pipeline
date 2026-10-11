 
"""Unit and integration tests for Member 2 (PDF & OCR Extraction)."""

from __future__ import annotations

from pathlib import Path
import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from src.common.schema import Document, TextBlock
from src.extractors.ocr import ocr_image, preprocess_image
from src.extractors.pdf_extractor import PDFExtractionError, PDFExtractor, extract_pdf
from src.router import route_and_extract

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def sample_pdf_paths() -> dict[str, Path]:
    digital_pdf = DATA_DIR / "sample_digital_policy_pii.pdf"
    scanned_pdf = DATA_DIR / "sample_scanned_policy_pii.pdf"

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    page.insert_text((50, 50), "Cadence Financial - Wire Transfer Control Policy", fontsize=18)
    page.insert_text((50, 85), "1. Control Owners & Escalation Contacts", fontsize=14)
    page.insert_text(
        (50, 110),
        "Primary Control Owner: Vikramaditya Rao (Employee ID: EMP-77210)\n"
        "Corporate Email: vikram.rao@cadencebank.com | Direct Phone: +1-212-555-0148\n"
        "Backup Reviewer: Sarah Jenkins | SSN: 412-88-9021 | DOB: 22/11/1988",
        fontsize=11,
    )

    x0, y0, col_w, row_h = 50, 180, 160, 25
    table_data = [
        ["Employee ID", "Full Name", "Tax ID / PAN"],
        ["EMP-90124", "Ananya Sharma", "ABCDE1234F"],
        ["EMP-90552", "Marcus Vance", "384-92-1049"],
    ]
    for r_idx, row in enumerate(table_data):
        for c_idx, val in enumerate(row):
            rx0 = x0 + c_idx * col_w
            ry0 = y0 + r_idx * row_h
            rect = fitz.Rect(rx0, ry0, rx0 + col_w, ry0 + row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=1)
            page.insert_text((rx0 + 6, ry0 + 16), val, fontsize=10)

    doc.save(digital_pdf)

    pix = page.get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), 2.0, 1.0)
    skewed = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))
    noise = np.random.normal(0, 4, skewed.shape).astype(np.int16)
    noisy = np.clip(skewed.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    _, png_bytes = cv2.imencode(".png", noisy)
    sdoc = fitz.open()
    spage = sdoc.new_page(width=612, height=792)
    spage.insert_image(spage.rect, stream=png_bytes.tobytes())
    sdoc.save(scanned_pdf)

    doc.close()
    sdoc.close()

    return {"digital": digital_pdf, "scanned": scanned_pdf}


def test_digital_pdf_extraction_and_schema(sample_pdf_paths: dict[str, Path]) -> None:
    doc = extract_pdf(sample_pdf_paths["digital"])
    assert isinstance(doc, Document)
    assert doc.file_type == "pdf"
    assert doc.document_id == "doc_sample_digital_policy_pii"
    assert doc.metadata["digital_pages"] == 1
    assert doc.metadata["scanned_pages"] == 0
    assert len(doc.blocks) > 0

    all_text = " ".join(b.text for b in doc.blocks)
    assert "EMP-77210" in all_text
    assert "vikram.rao@cadencebank.com" in all_text
    assert "412-88-9021" in all_text
    assert "ABCDE1234F" in all_text

    block_types = {b.metadata.get("block_type") for b in doc.blocks}
    assert "paragraph" in block_types
    assert "table_cell" in block_types
    assert any(b.metadata.get("is_heading") is True for b in doc.blocks)


def test_router_dispatches_pdf_to_member2(sample_pdf_paths: dict[str, Path]) -> None:
    doc = route_and_extract(sample_pdf_paths["digital"])
    assert isinstance(doc, Document)
    assert doc.file_type == "pdf"
    assert len(doc.blocks) >= 5


def test_image_preprocessing_deskew_denoise_binarize(sample_pdf_paths: dict[str, Path]) -> None:
    fdoc = fitz.open(sample_pdf_paths["scanned"])
    img_bytes = fdoc[0].get_pixmap(dpi=150).tobytes("png")
    fdoc.close()

    cleaned, meta = preprocess_image(img_bytes)
    assert isinstance(cleaned, np.ndarray)
    assert len(cleaned.shape) == 2
    assert meta["denoised"] is True
    assert meta["deskewed"] is True
    assert meta["binarized"] is True


def test_scanned_pdf_and_shared_ocr_function(sample_pdf_paths: dict[str, Path]) -> None:
    doc = extract_pdf(sample_pdf_paths["scanned"])
    assert isinstance(doc, Document)
    assert doc.metadata["scanned_pages"] == 1
    assert len(doc.blocks) >= 1
    assert all(isinstance(b, TextBlock) for b in doc.blocks)
    assert "low_confidence_flag" in doc.blocks[0].metadata

    fdoc = fitz.open(sample_pdf_paths["scanned"])
    img_bytes = fdoc[0].get_pixmap(dpi=150).tobytes("png")
    fdoc.close()
    res = ocr_image(img_bytes)
    assert "text" in res
    assert "confidence" in res
    assert "low_confidence_flag" in res


def test_pdf_extractor_validation_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_pdf(tmp_path / "missing.pdf")

    bad_ext = tmp_path / "not_a_pdf.txt"
    bad_ext.write_text("hello")
    with pytest.raises(ValueError):
        extract_pdf(bad_ext)

    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"not a valid pdf header")
    with pytest.raises(PDFExtractionError):
        PDFExtractor().extract(corrupt_pdf)
