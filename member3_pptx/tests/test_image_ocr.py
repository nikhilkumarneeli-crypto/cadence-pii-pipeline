"""Image OCR Extraction & Adapter Tests for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
"""

from pathlib import Path
import pytest
from src.pptx_extractor.extractor import PPTXExtractor
from src.pptx_extractor.image_ocr import (
    ImageOCRExtractor,
    MockOCRAdapter,
    TesseractOCRAdapter,
    Member2OCRAdapter,
)


@pytest.fixture
def pptx_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "test_data" / "pptx"


def test_tesseract_adapter_status_reporting():
    """Verify Tesseract adapter transparently reports status and installation instructions."""
    adapter = TesseractOCRAdapter()
    msg = adapter.get_status_message()
    assert msg is not None
    assert len(msg) > 10

    # If tesseract binary is not on host, is_available must be False
    if not adapter.tesseract_cmd:
        assert adapter.is_available() is False
        assert "winget install UB-Mannheim.TesseractOCR" in msg


def test_member2_ocr_adapter_interface():
    """Verify Member 2 shared adapter interface behaves safely before Member 2 is loaded."""
    m2 = Member2OCRAdapter()
    assert m2.is_available() is False
    assert "Member 2" in m2.get_status_message()
    text, conf, meta = m2.run_ocr(b"fake_image_bytes")
    assert text == ""
    assert conf == 0.0
    assert meta["status"] == "member2_ocr_not_available"


def test_mock_ocr_adapter_pipeline(pptx_dir: Path):
    """Verify end-to-end image extraction using MockOCRAdapter."""
    mock_adapter = MockOCRAdapter(
        predefined_text="CADENCE EMPLOYEE BADGE: Kevin O'Connor | k.oconnor@cadencefg.example",
        confidence=0.96
    )
    extractor = PPTXExtractor(ocr_adapter=mock_adapter)

    p_path = pptx_dir / "test4_image_ocr_pii.pptx"
    result = extractor.extract(p_path)

    ocr_blocks = [b for b in result.blocks if b.block_type == "image_ocr"]
    assert len(ocr_blocks) == 2

    for b in ocr_blocks:
        assert "Kevin O'Connor" in b.text
        assert b.confidence == 0.96
        assert b.source_type == "image_ocr"
        assert b.ocr_metadata is not None
        assert b.ocr_metadata["ocr_confidence"] == 0.96


def test_image_extraction_without_ocr_binary(pptx_dir: Path):
    """Verify image shapes are extracted and documented even if Tesseract binary is missing."""
    extractor = PPTXExtractor()  # Uses default system adapter
    p_path = pptx_dir / "test4_image_ocr_pii.pptx"
    result = extractor.extract(p_path)

    ocr_blocks = [b for b in result.blocks if b.block_type == "image_ocr"]
    assert len(ocr_blocks) == 2
    for b in ocr_blocks:
        assert b.block_id.startswith("s1_img_")
        assert b.position.width > 0
